# FakeScope Security Hub Backend

Scam detection backend for Indian users powered by FastAPI and Google Gemini 2.5 Flash.

## File Structure
```
fakescope-backend/
├── main.py                  # FastAPI Application Setup & Entrypoint
├── Dockerfile               # Docker configuration for deployment (with Tesseract OCR)
├── requirements.txt         # Project Dependencies
├── routes/
│   ├── text_route.py        # Text scam detection route (/check-text)
│   ├── image_route.py       # Image OCR & analysis route (/check-image)
│   └── deepfake_route.py    # Deepfake detection route (/check-deepfake)
├── services/
│   └── gemini_service.py    # Gemini API wrapper with lazy client initialization
└── models/
    └── schemas.py           # Shared request/response Pydantic models
```

## Local Setup

1. **Create Virtual Environment**:
   ```bash
   python3 -m venv venv
   source venv/bin/activate
   pip install -r requirements.txt
   ```

2. **Configure Environment Variables**:
   Create a `.env` file in the root directory:
   ```env
   GEMINI_API_KEY=your_gemini_api_key_here
   SIGHTENGINE_API_USER=your_sightengine_api_user_here
   SIGHTENGINE_API_SECRET=your_sightengine_api_secret_here
   ```

3. **Install Tesseract OCR (Required for `/check-image`):**
   - **macOS**: `brew install tesseract`
   - **Ubuntu/Debian**: `sudo apt-get install tesseract-ocr`

4. **Run Server**:
   ```bash
   uvicorn main:app --reload
   ```
   Open [http://localhost:8000/docs](http://localhost:8000/docs) to access the interactive Swagger API documentation.

## API Specification & JSON Contract

### POST `/check-text`
Accepts a raw text message (SMS, WhatsApp, Email, URL).
**Request Body:**
```json
{
  "text": "Dear customer, your SBI KYC has expired. Please click http://bit.ly/sbi-kyc immediately to avoid blocking."
}
```

### POST `/check-image`
Accepts an image file (`multipart/form-data`). Extracts text via Tesseract OCR and analyzes it for scam indicators. Returns the standard scan result structure with an additional `extracted_text` field.

### POST `/check-deepfake`
Accepts an image file (`multipart/form-data`). Calls SightEngine's generation model to check if the image is synthetic/AI-generated.

### Response JSON Schema (All endpoints return this structure)
```json
{
  "danger_score": 98,
  "type": "scam",
  "scam_category": "kyc",
  "red_flags": [
    "Urgent tone to create panic",
    "Threat of service blocking"
  ],
  "explanation": "This is a phishing attempt mimicking an SBI card block threat to steal user credentials.",
  "precautions": [
    "Do not click the link provided.",
    "Verify by calling your bank directly."
  ],
  "block_recommended": true,
  "report_to": "cybercrime.gov.in"
}
```

## Production Deployment (Render)

This project is configured to build using **Docker** to ensure Tesseract OCR libraries are correctly installed.

1. Connect this repository to your **Render Web Service**.
2. Select **Docker** as the Runtime (Render will automatically detect the `Dockerfile`).
3. Set the following environment variables in the Render settings tab:
   - `GEMINI_API_KEY`
   - `SIGHTENGINE_API_USER`
   - `SIGHTENGINE_API_SECRET`
4. Click **Deploy**.
