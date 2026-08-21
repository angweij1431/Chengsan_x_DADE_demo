import streamlit as st
from streamlit_drawable_canvas import st_canvas
from PIL import Image
import requests
import io

# --- Configuration & Setup ---
st.set_page_config(page_title="AI Void Deck Makeover", layout="wide")

# Insert your Hugging Face Token here (starts with hf_)
API_TOKEN = "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" 

# Updated Hugging Face Router URL for the supported v1.5 Inpainting model
API_URL = "https://router.huggingface.co/hf-inference/models/stable-diffusion-v1-5/stable-diffusion-inpainting"

@st.cache_data
def load_and_resize_image(image_file, target_size=(512, 512)):
    img = Image.open(image_file).convert("RGB")
    return img.resize(target_size)

# --- 0. The File Uploader ---
st.markdown("<h2 style='text-align: center;'>0. UPLOAD YOUR BASE IMAGE</h2>", unsafe_allow_html=True)
uploaded_file = st.file_uploader("Choose an image from your laptop...", type=["jpg", "jpeg", "png"])

if uploaded_file is not None:
    bg_image = load_and_resize_image(uploaded_file)

    st.markdown("<h1 style='text-align: center; font-size: 50px; color: #FF4B4B;'>1. DRAW OVER THE AREA TO CHANGE!</h1>", unsafe_allow_html=True)
    st.markdown("<p style='text-align: center; font-size: 24px;'>Use your mouse to paint over the benches, floor, or pillars.</p>", unsafe_allow_html=True)

    col1, col2 = st.columns([2, 1])

    with col1:
        canvas_result = st_canvas(
            fill_color="rgba(255, 255, 255, 1)", 
            stroke_width=30,                     
            stroke_color="#FFFFFF",              
            background_image=bg_image,
            height=bg_image.height,
            width=bg_image.width,
            drawing_mode="freedraw",
            key="canvas",
        )

    with col2:
        st.markdown("<h2 style='font-size: 35px;'>2. CHOOSE A VISION</h2>", unsafe_allow_html=True)
        
        chosen_prompt = ""
        if st.button("🍜 Cyberpunk Hawker Stall", use_container_width=True): chosen_prompt = "A futuristic cyberpunk hawker stall with neon lights"
        if st.button("🌿 Lush Botanical Garden", use_container_width=True): chosen_prompt = "A lush indoor botanical garden with hanging plants and vines"
        if st.button("🚀 Space Kampong", use_container_width=True): chosen_prompt = "A retro-futuristic spaceship interior kampong"
        if st.button("🤖 Robot Uncle Playing Chess", use_container_width=True): chosen_prompt = "A friendly robot uncle sitting at a table"
        
        st.markdown("### OR WRITE YOUR OWN:")
        custom_prompt = st.text_input("Enter your idea here...")
        
        final_prompt = custom_prompt if custom_prompt else chosen_prompt

        if final_prompt:
            st.info(f"**Current Idea:** {final_prompt}")

        if st.button("✨ AI MAKE IT! ✨", type="primary", use_container_width=True):
            if canvas_result.image_data is None:
                st.error("Please draw on the image first!")
            elif not final_prompt:
                st.error("Please select or type an idea!")
            else:
                with st.spinner("Wait ah, AI is thinking... (Usually takes 10-30 seconds on free tier)"):
                    try:
                        # 1. Process Mask
                        mask_data = canvas_result.image_data
                        mask_image = Image.fromarray(mask_data.astype('uint8'), 'RGBA')
                        
                        background = Image.new("RGB", mask_image.size, (0, 0, 0))
                        background.paste(mask_image, mask=mask_image.split()[3])
                        mask_bw = background.convert("L")

                        # 2. Convert Images to Bytes
                        img_byte_arr = io.BytesIO()
                        bg_image.save(img_byte_arr, format='JPEG')
                        img_bytes = img_byte_arr.getvalue()

                        mask_byte_arr = io.BytesIO()
                        mask_bw.save(mask_byte_arr, format='JPEG')
                        mask_bytes = mask_byte_arr.getvalue()

                        # 3. Call Hugging Face API
                        headers = {"Authorization": f"Bearer {API_TOKEN}"}
                        
                        response = requests.post(API_URL, headers=headers, files={
                            "image": img_bytes,
                            "mask_image": mask_bytes
                        }, data={"inputs": final_prompt})
                        
                        if response.status_code == 200:
                            result_image = Image.open(io.BytesIO(response.content))
                            st.markdown("<h2 style='text-align: center; color: #4CAF50;'>3. YOUR NEW VOID DECK</h2>", unsafe_allow_html=True)
                            st.image(result_image, use_container_width=True)
                            st.balloons()
                        elif response.status_code == 503:
                            st.error("Model is currently loading on the server. Please wait a minute and click 'AI Make It!' again.")
                        else:
                            st.error(f"API Error: {response.status_code} - {response.text}")
                            
                    except Exception as e:
                        st.error(f"Connection failed: {e}")
                        
else:
    st.info("👆 Please upload a photo to start the experience!")