import streamlit as st
import requests
import os
from dotenv import load_dotenv
import uuid # For generating unique session IDs

# Load environment variables from .env file
load_dotenv()

# --- Configuration from Environment Variables ---
ANYTHINGLLM_API_URL = os.environ.get("ANYTHINGLLM_API_URL") # e.g., "http://localhost:3001"
ANYTHINGLLM_API_KEY = os.environ.get("ANYTHINGLLM_API_KEY")
ANYTHINGLLM_WORKSPACE_ID = os.environ.get("ANYTHINGLLM_WORKSPACE_ID") # e.g., "hometasks"

# --- Input Validation for Configuration ---
if ANYTHINGLLM_API_URL is None:
    st.error("Ortam değişkeni ANYTHINGLLM_API_URL ayarlanmamış. Lütfen .env dosyanızı veya ortam değişkenlerinizi kontrol edin.")
    st.stop()
if ANYTHINGLLM_API_KEY is None:
    st.error("Ortam değişkeni ANYTHINGLLM_API_KEY ayarlanmamış. Lütfen .env dosyanızı veya ortam değişkenlerinizi kontrol edin.")
    st.stop()
if ANYTHINGLLM_WORKSPACE_ID is None:
    st.error("Ortam değişkeni ANYTHINGLLM_WORKSPACE_ID ayarlanmamış. Lütfen .env dosyanızı veya ortam değişkenlerinizi kontrol edin.")
    st.stop()

# --- Streamlit UI Setup ---
st.title("AnythingLLM Destekli Akıllı Chatbot")

# Initialize chat history in session state
if "messages" not in st.session_state:
    st.session_state["messages"] = [{"role": "assistant", "content": "Merhaba! Nasıl yardımcı olabilirim?"}]

# Initialize a unique session ID for AnythingLLM to manage chat history
if "session_id" not in st.session_state:
    st.session_state["session_id"] = str(uuid.uuid4()) # Generate a UUID for the session

# Display existing chat messages
for msg in st.session_state["messages"]:
    st.chat_message(msg["role"]).write(msg["content"])

# --- Chat Input and API Interaction ---
if prompt := st.chat_input("Buraya bir soru yazın..."):
    # Add user message to chat history
    st.session_state["messages"].append({"role": "user", "content": prompt})
    st.chat_message("user").write(prompt)

    with st.spinner("Yanıt oluşturuluyor..."):
        try:
            # Construct the full API endpoint URL
            # Note: The workspaceId is part of the URL path as per your documentation
            api_endpoint = f"{ANYTHINGLLM_API_URL}/v1/workspace/{ANYTHINGLLM_WORKSPACE_ID}/chat"

            headers = {
                "Authorization": f"Bearer {ANYTHINGLLM_API_KEY}",
                "Content-Type": "application/json",
                "accept": "application/json" # Explicitly setting accept header
            }

            # Construct the request body as per AnythingLLM documentation
            payload = {
                "message": prompt, # The user's query
                "mode": "chat",   # Or "query" if you want to strictly use vectorDB sources
                "sessionId": st.session_state["session_id"], # Unique ID for AnythingLLM to track history
                "reset": False    # Set to True if you want to reset the chat history for this sessionId
            }

            # --- Debugging Output (Optional, remove in production) ---
            st.sidebar.markdown("--- Debug Bilgileri ---")
            st.sidebar.write(f"API Hedef URL: {api_endpoint}")
            st.sidebar.write(f"Gönderilen Başlıklar: {headers}")
            st.sidebar.write(f"Gönderilen Payload: {payload}")
            st.sidebar.markdown("---")
            # --- End Debugging Output ---

            response = requests.post(api_endpoint, headers=headers, json=payload)

            # Check for HTTP errors (e.g., 403 Forbidden, 400 Bad Request, 500 Internal Server Error)
            response.raise_for_status() 

            # Parse the JSON response
            api_response_data = response.json()

            # Check if AnythingLLM returned an error within its JSON structure
            if api_response_data.get("error") and api_response_data["error"] != "null":
                assistant_response = f"API'den bir hata alındı: {api_response_data['error']}"
                st.error(assistant_response)
            elif "textResponse" in api_response_data:
                assistant_response = api_response_data["textResponse"]
                
                # Optionally, display source documents
                if "sources" in api_response_data and api_response_data["sources"]:
                    source_titles = ", ".join([s["title"] for s in api_response_data["sources"]])
                    assistant_response += f"\n\nKaynaklar: {source_titles}"

            else:
                assistant_response = "AnythingLLM API'sinden beklenmedik bir yanıt formatı alındı."
                st.error(f"Beklenmedik yanıt: {api_response_data}")

            # Add assistant's response to chat history
            st.session_state["messages"].append({"role": "assistant", "content": assistant_response})
            st.chat_message("assistant").write(assistant_response)

        except requests.exceptions.HTTPError as e:
            # Handle specific HTTP errors
            error_message = f"API isteği sırasında bir HTTP hatası oluştu: {e}"
            if response.status_code == 403:
                try:
                    error_details = response.json().get("error", "API anahtarı hatası.")
                    error_message = f"Erişim Reddedildi (403): {error_details}. API anahtarınızı kontrol edin."
                except requests.exceptions.JSONDecodeError:
                    error_message = f"Erişim Reddedildi (403): Geçersiz API anahtarı veya yetkilendirme sorunu."
            elif response.status_code == 400:
                 try:
                    error_details = response.json().get("message", "Geçersiz istek.")
                    error_message = f"Geçersiz İstek (400): {error_details}. İstek gövdesini kontrol edin."
                 except requests.exceptions.JSONDecodeError:
                    error_message = f"Geçersiz İstek (400): AnythingLLM'e gönderilen istek yanlış formatta."

            st.error(error_message)
            st.sidebar.write(f"API Ham Yanıt Durum Kodu: {response.status_code}")
            st.sidebar.write(f"API Ham Yanıt Metni: {response.text}")

        except requests.exceptions.RequestException as e:
            st.error(f"API isteği sırasında bir bağlantı hatası oluştu: {e}")
            st.sidebar.write(f"API Ham Yanıt Durum Kodu: {response.status_code if 'response' in locals() else 'N/A'}")
            st.sidebar.write(f"API Ham Yanıt Metni: {response.text if 'response' in locals() else 'N/A'}")

        except (KeyError, ValueError, requests.exceptions.JSONDecodeError) as e:
            st.error(f"API yanıtı işlenirken bir hata oluştu: {e}. Yanıt formatı beklenenden farklı olabilir.")
            st.sidebar.write(f"API Ham Yanıt Metni (JSONDecodeError öncesi): {response.text if 'response' in locals() else 'N/A'}")