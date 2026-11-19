from fastapi import FastAPI

app= FastAPI(
    title= "Taskflow API",
    description= "Kullanıcı, proje ve görev yönetimi için REST API",
    version= "0.1.0",
)

@app.get("/")
def root():
    return {
        "message": "Taskflow API çalışıyor!",
        "version": "0.1.0"
    }

@app.get("/health")
def health_check():
    return {
        "status": "healthy",
        "message": "API sağlıklı bir şekilde çalışıyor."
    }

