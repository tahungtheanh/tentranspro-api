from fastapi import FastAPI, File, UploadFile, Form
from fastapi.responses import JSONResponse, FileResponse
from fastapi.middleware.cors import CORSMiddleware
import shutil, os, uuid
import openai
import pandas as pd
from docx import Document

openai.api_key = "sk-..."  # Thay bằng API key của bạn

app = FastAPI()

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

UPLOAD_DIR = "uploaded"
RESULT_DIR = "translated"
os.makedirs(UPLOAD_DIR, exist_ok=True)
os.makedirs(RESULT_DIR, exist_ok=True)

async def translate_text(text, source_lang="zh", target_lang="vi"):
    if not text.strip():
        return ""
    prompt = f"Dịch sang tiếng Việt và trình bày song ngữ:\n\nTiếng Trung:\n{text}\n\nTiếng Việt:"
    response = openai.ChatCompletion.create(
        model="gpt-4",
        messages=[{"role": "user", "content": prompt}],
        temperature=0.5,
    )
    return response.choices[0].message["content"]

@app.post("/translate")
async def translate_file(file: UploadFile = File(...),
                          source_lang: str = Form(...),
                          target_lang: str = Form(...),
                          format: str = Form(...)):
    file_id = str(uuid.uuid4())
    input_path = os.path.join(UPLOAD_DIR, f"{file_id}_{file.filename}")
    output_path = os.path.join(RESULT_DIR, f"translated_{file.filename}")

    with open(input_path, "wb") as buffer:
        shutil.copyfileobj(file.file, buffer)

    ext = file.filename.split(".")[-1]

    if ext in ["xlsx", "xls"]:
        df = pd.read_excel(input_path, header=None)
        for i in range(df.shape[0]):
            for j in range(df.shape[1]):
                try:
                    text = str(df.iat[i, j])
                    translated = await translate_text(text, source_lang, target_lang)
                    df.iat[i, j] = f"{text}\n{translated}"
                except:
                    continue
        df.to_excel(output_path, index=False, header=False)

    elif ext in ["docx"]:
        doc = Document(input_path)
        for para in doc.paragraphs:
            translated = await translate_text(para.text, source_lang, target_lang)
            para.text = f"{para.text}\n{translated}"
        doc.save(output_path)

    else:
        return JSONResponse({"error": "Định dạng chưa hỗ trợ"}, status_code=400)

    return {"translated_file_url": f"/download/{os.path.basename(output_path)}"}

@app.get("/download/{filename}")
async def download_file(filename: str):
    path = os.path.join(RESULT_DIR, filename)
    if not os.path.exists(path):
        return JSONResponse({"error": "Không tìm thấy file"}, status_code=404)
    return FileResponse(path)
