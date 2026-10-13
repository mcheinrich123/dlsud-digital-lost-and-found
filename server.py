


from fastapi import FastAPI, HTTPException, UploadFile, File
from fastapi.responses import HTMLResponse
from pydantic import BaseModel
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.metrics.pairwise import cosine_similarity
from PIL import Image
import io



app = FastAPI(title=" De La Salle University - Dasmariñas University Digital Lost & Found Back-End Development with Image Support")

# ---------------------------------------------------------
# MOCK DATABASE (With Added Image/Tag context)
# ---------------------------------------------------------
found_items_db = [
    {"id": 1, "category": "Electronics", "location": "Main Library", "description": "Black Dell laptop with a cracked screen corner", "ai_tags": "black dell laptop computer electronics"},
    {"id": 2, "category": "Bags", "location": "Gym Locker Room", "description": "Red Nike backpack containing a blue water bottle", "ai_tags": "red nike backpack bag bottle"},
    {"id": 3, "category": "Electronics", "location": "Science Pavilion", "description": "Black Apple MacBook laptop in a brown leather sleeve", "ai_tags": "black apple macbook laptop computer leather"},
    {"id": 4, "category": "Keys", "location": "Student Union Cafeteria", "description": "Silver metal keys with a red car keychain", "ai_tags": "silver metal keys keychain red"},
    {"id": 5, "category": "Wallets", "location": "Engineering Block", "description": "Brown leather bi-fold wallet with a student ID inside", "ai_tags": "brown leather wallet money id"}
]

class SearchRequest(BaseModel):
    query: str

# ---------------------------------------------------------
# IMAGE MATCHING ENDPOINT (Component 2 & 3)
# ---------------------------------------------------------
@app.post("/search-image")
async def search_by_image(file: UploadFile = File(...)):
    # 1. Ensure the uploaded file is actually an image
    if not file.content_type.startswith("image/"):
        raise HTTPException(status_code=400, detail="Uploaded file must be an image.")
    
    try:
        # 2. Read the image binary data
        image_bytes = await file.read()
        image = Image.open(io.BytesIO(image_bytes))
        
        # [SIMULATION] In a production environment, an AI model like CLIP or YOLOv8 
        # would analyze the pixel layout here. We simulate this by checking dimensions 
        # to guess if it's a laptop/bag or text tags.
        width, height = image.size
        
        # We generate simulated search keywords based on the file metadata/aspect ratio
        if width > height:
            simulated_ai_query = "black laptop computer electronics"
        else:
            simulated_ai_query = "backpack red bag"
            
        # 3. Match using our existing TF-IDF logic against database AI tags
        corpus = [simulated_ai_query] + [item["ai_tags"] for item in found_items_db]
        vectorizer = TfidfVectorizer(stop_words='english')
        tfidf_matrix = vectorizer.fit_transform(corpus)
        similarity_scores = cosine_similarity(tfidf_matrix[0:1], tfidf_matrix)
        
        matched_results = []
        for index, item in enumerate(found_items_db):
            score = similarity_scores[index + 1]
            match_percentage = round(float(score) * 100, 2)
            
            if match_percentage > 0:
                matched_results.append({
                    "id": item["id"],
                    "category": item["category"],
                    "location": item["location"],
                    "description": item["description"],
                    "match_score": f"{match_percentage}%"
                })
                
        matched_results.sort(key=lambda x: float(x["match_score"].replace("%", "")), reverse=True)
        
        return {
            "file_name": file.filename,
            "detected_dimensions": f"{width}x{height}",
            "simulated_ai_analysis": f"AI detected properties closest to: {simulated_ai_query}",
            "matches": matched_results
        }
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error processing image: {str(e)}")

# ---------------------------------------------------------
# VISUAL DRAG & DROP FRONTEND (Component 1)
# ---------------------------------------------------------
@app.get("/", response_class=HTMLResponse)
def test_interface():
    return """
    <!DOCTYPE html>
    <html>
    <head>
        <title>Campus Lost & Found Test Portal</title>
        <style>
            body { font-family: Arial, sans-serif; max-width: 600px; margin: 40px auto; padding: 20px; background-color: #fcfbf7; text-align: center; }
            #drop-zone { border: 3px dashed #b5a46d; border-radius: 10px; padding: 60px 20px; background-color: #fff; cursor: pointer; transition: 0.3s; }
            #drop-zone.hover { background-color: #f1ebd9; }
            #results { margin-top: 30px; text-align: left; background: #fff; padding: 15px; border-radius: 8px; border: 1px solid #ddd; display: none; }
            .match-item { padding: 8px; border-bottom: 1px solid #eee; }
            .score { color: green; font-weight: bold; }
        </style>
    </head>
    <body>
        <h2>🎒 Campus Lost & Found System</h2>
        <p>Drag and drop a photo of your lost item below to test the matching pipeline:</p>
        
        <div id="drop-zone">Drag & Drop Image Here or Click to Upload</div>
        <input type="file" id="file-input" accept="image/*" style="display: none;">
        
        <div id="results">
            <h3>Top System Matches:</h3>
            <div id="meta"></div>
            <hr>
            <div id="match-list"></div>
        </div>

        <script>
            const dropZone = document.getElementById('drop-zone');
            const fileInput = document.getElementById('file-input');
            const resultsDiv = document.getElementById('results');

            dropZone.addEventListener('click', () => fileInput.click());
            dropZone.addEventListener('dragover', (e) => { e.preventDefault(); dropZone.classList.add('hover'); });
            dropZone.addEventListener('dragleave', () => dropZone.classList.remove('hover'));
            dropZone.addEventListener('drop', (e) => {
                e.preventDefault();
                dropZone.classList.remove('hover');
                if (e.dataTransfer.files.length) handleUpload(e.dataTransfer.files[0]);
            });
            fileInput.addEventListener('change', (e) => {
                if (fileInput.files.length) handleUpload(fileInput.files[0]);
            });

            function handleUpload(file) {
                const formData = new FormData();
                formData.append('file', file);
                dropZone.innerText = "Analyzing item properties...";

                fetch('/search-image', { method: 'POST', body: formData })
                .then(res => res.json())
                .then(data => {
                    dropZone.innerText = "Drag & Drop Image Here or Click to Upload";
                    resultsDiv.style.display = 'block';
                    document.getElementById('meta').innerHTML = `<i>Processed: ${data.file_name} (${data.detected_dimensions})<br>${data.simulated_ai_analysis}</i>`;
                    
                    let html = '';
                    if(data.matches.length === 0) { html = '<p>No matches found.</p>'; }
                    data.matches.forEach(item => {
                        html += `<div class="match-item"><span class="score">[${item.match_score}]</span> <b>ID ${item.id} (${item.category}):</b> ${item.description} (Found at: ${item.location})</div>`;
                    });
                    document.getElementById('match-list').innerHTML = html;
                })
                .catch(err => { alert('Upload failed'); dropZone.innerText = "Error, try again"; });
            }
        </script>
    </body>
    </html>
    """
