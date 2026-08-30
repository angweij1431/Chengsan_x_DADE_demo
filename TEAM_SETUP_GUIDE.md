# Teammate & Local Development Onboarding Guide

This guide explains how to set up the **Firebase Firestore Database**, configure environment credentials, and share setup instructions with your teammates so everyone can develop locally.

---

## 1. Setting Up Your Firebase Firestore Project

Follow these steps to create and configure your Firebase project:

### Step 1: Create Firebase Project
1. Open the [Firebase Console](https://console.firebase.google.com/).
2. Click **Create a project** (or **Add project**).
3. Name your project (e.g. `grooveai-dance-studio`) and click **Continue**.
4. (Optional) Disable or enable Google Analytics, then click **Create project**.

### Step 2: Enable Firestore Database
1. In the left sidebar, click **Build** ➔ **Firestore Database**.
2. Click **Create database**.
3. Select your location (e.g., `asia-southeast1` for Singapore/Asia or `us-central1`).
4. Select **Start in test mode** (allows read/write during development) or **production mode**, then click **Enable**.

### Step 3: Download Firebase Admin SDK Key (`serviceAccountKey.json`)
1. Click the ⚙️ **Project Settings** (gear icon at top left next to *Project Overview*).
2. Go to the **Service accounts** tab.
3. Ensure **Python** is selected under the *Admin SDK configuration snippet*.
4. Click **Generate new private key**, then confirm by clicking **Generate key**.
5. A `.json` credential file will download to your computer.
6. Rename this file to **`serviceAccountKey.json`** and save it into the root directory of your project folder.

> [!IMPORTANT]
> **Security Notice**: `serviceAccountKey.json` contains administrative access keys to your database. It is already added to `.gitignore` so git will **never** commit or push this file to GitHub.

---

## 2. Cloudinary & Environment Setup

1. Sign up for a free account at [Cloudinary](https://cloudinary.com/).
2. Go to your **Cloudinary Dashboard** to find:
   - **Cloud Name**
   - **API Key**
   - **API Secret**

---

## 3. How Teammates Set Up Locally (Developer Onboarding)

Send your teammates these quick steps to get them running locally in under 5 minutes:

### 📥 Step 1: Clone & Checkout
```bash
git clone https://github.com/angweij1431/Chengsan_x_DADE_demo.git
cd Chengsan_x_DADE_demo
git checkout main
```

### 🐍 Step 2: Virtual Environment & Dependencies
```bash
# Create virtual environment
python -m venv .venv

# Activate virtual environment
# Windows (PowerShell):
.venv\Scripts\Activate.ps1
# Mac/Linux:
source .venv/bin/activate

# Install requirements
pip install -r requirements.txt
```

### 🔑 Step 3: Environment Credentials
1. Copy `.env.example` to `.env`:
   ```bash
   cp .env.example .env
   ```
2. Paste the shared Cloudinary and Firebase environment settings into `.env`:
   ```env
   PORT=5000
   DB_TYPE=firestore
   FIREBASE_CREDENTIALS_PATH=serviceAccountKey.json

   CLOUDINARY_CLOUD_NAME=your_cloud_name
   CLOUDINARY_API_KEY=your_api_key
   CLOUDINARY_API_SECRET=your_api_secret

   AI_API_KEY=your_replicate_or_dace_api_key
   ```
3. Save the shared **`serviceAccountKey.json`** file in the root project folder.

> [!NOTE]
> **Frictionless Mock Mode**: If a teammate hasn't set up `serviceAccountKey.json` yet, the app automatically falls back to in-memory testing mode—allowing frontend developers to test the full UI without needing database keys!

### 🚀 Step 4: Run Application Locally
```bash
python app.py
```
Open **`http://localhost:5000`** in your browser.

---

## ⚡ 4. Where Teammates Plug In the Real AI Bodyswapping Model

When your team builds or connects the actual AI body-swapping model (e.g. via Replicate, Runway, or custom endpoint):

1. Add your AI service token to `.env`:
   ```env
   AI_API_KEY=r8_your_replicate_token_here
   ```
2. Open **[generate_video.py](file:///c:/Users/User/git_projects/chengsan_dade/generate_video.py)** inside `generate_ai_dance_video()` (line 39-75):
   ```python
   # Modify payload to match your specific AI bodyswap model schema
   payload = {
       "version": "your_model_version_id",
       "input": {
           "source_motion_video": source_dance_path,
           "target_identity_image": user_person_path,
           "dance_style": dance_style,
           "max_duration_seconds": 8
       }
   }
   ```
