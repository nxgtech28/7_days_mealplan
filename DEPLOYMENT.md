# Deployment Guide

This guide will help you deploy your Meal Planner API so others can access it via Postman.

## 🚀 Quick Deployment Options

### Option 1: Railway (Recommended - Easiest)

1. **Sign up for Railway**
   - Go to https://railway.app
   - Sign up with GitHub

2. **Create New Project**
   - Click "New Project"
   - Select "Deploy from GitHub repo"
   - Choose your repository: `7_Days_mealsplan`

3. **Add Environment Variables**
   - In your Railway project, go to "Variables" tab
   - Add these variables:
     ```
     GROQ_API_KEY = your_actual_groq_api_key_here
     GROQ_MODEL = llama-3.3-70b-versatile
     PORT = 8000
     ```

4. **Deploy**
   - Railway will automatically detect the Dockerfile and deploy
   - Wait for deployment to complete (2-3 minutes)

5. **Get Your Public URL**
   - Railway will provide a public URL like: `https://your-app-name.up.railway.app`
   - Share this URL with others for Postman testing

---

### Option 2: Render (Free Tier)

1. **Sign up for Render**
   - Go to https://render.com
   - Sign up with GitHub

2. **Create New Web Service**
   - Click "New +" → "Web Service"
   - Connect your GitHub repository: `7_Days_mealsplan`
   - Select the repository

3. **Configure Service**
   - **Name**: `meal-planner-api` (or any name)
   - **Environment**: `Python 3`
   - **Build Command**: `pip install -r requirements.txt`
   - **Start Command**: `uvicorn main:app --host 0.0.0.0 --port $PORT`

4. **Add Environment Variables**
   - Scroll to "Environment Variables"
   - Add:
     ```
     GROQ_API_KEY = your_actual_groq_api_key_here
     GROQ_MODEL = llama-3.3-70b-versatile
     ```

5. **Deploy**
   - Click "Create Web Service"
   - Wait for deployment (3-5 minutes)

6. **Get Your Public URL**
   - Render provides: `https://your-app-name.onrender.com`
   - Share this URL for Postman testing

---

### Option 3: ngrok (Quick Testing - Temporary)

For quick testing without deploying:

1. **Install ngrok**
   - Download from https://ngrok.com/download
   - Or install via: `choco install ngrok` (Windows) or `brew install ngrok` (Mac)

2. **Start Your Local Server**
   ```bash
   python main.py
   ```
   Your API runs on `http://localhost:8000`

3. **Create ngrok Tunnel**
   ```bash
   ngrok http 8000
   ```

4. **Get Public URL**
   - ngrok will show a URL like: `https://abc123.ngrok.io`
   - This URL is temporary (free tier: 2 hours)
   - Share this URL for Postman testing

**Note**: Keep your local server and ngrok running while testing.

---

## 📝 Postman Setup for Others

Once deployed, share these details:

### Base URL
```
https://your-deployed-url.com
```

### Endpoints

1. **Generate Meal Plan**
   - **Method**: `POST`
   - **URL**: `https://your-deployed-url.com/mealplan`
   - **Headers**: 
     ```
     Content-Type: application/json
     ```
   - **Body** (raw JSON):
     ```json
     {
       "input_text": "I am a 25-year-old male, 70kg, 175cm, moderately active, want to lose weight. Prefer Kerala cuisine with non-veg options."
     }
     ```

2. **Get Food Alternative**
   - **Method**: `POST`
   - **URL**: `https://your-deployed-url.com/alternative`
   - **Headers**: 
     ```
     Content-Type: application/json
     ```
   - **Body** (raw JSON):
     ```json
     {
       "input_text": "emergency: 200g Rice"
     }
     ```

3. **API Documentation**
   - **URL**: `https://your-deployed-url.com/docs`
   - Interactive Swagger UI documentation

---

## 🔒 Security Notes

- ✅ `config.json` is now in `.gitignore` - your API key won't be committed
- ✅ Use environment variables in production (Railway/Render)
- ✅ Never share your API keys publicly
- ✅ The API has CORS enabled for all origins (you can restrict this later)

---

## 🐛 Troubleshooting

### Deployment fails
- Check that all files are committed to GitHub
- Verify environment variables are set correctly
- Check deployment logs for errors

### API returns 500 errors
- Verify `GROQ_API_KEY` is set correctly in environment variables
- Check that Groq API key is valid and has credits

### CORS errors in Postman
- CORS is already enabled for all origins
- If issues persist, check the deployment logs

---

## 📚 Additional Resources

- Railway Docs: https://docs.railway.app
- Render Docs: https://render.com/docs
- ngrok Docs: https://ngrok.com/docs

