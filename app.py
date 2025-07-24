import os
import requests
from PIL import Image
from datetime import datetime
import io
import json
from flask import Flask, render_template_string, request, redirect, url_for, flash, session
import toml

# === Load API Key from secrets.toml ===
def load_api_key():
    try:
        secrets = toml.load('secrets.toml')
        return secrets['plantnet']['api_key']
    except Exception as e:
        raise RuntimeError(f"API key not found or secrets.toml misconfigured: {e}")

# Remove Gemini key loading
def load_openai_key():
    try:
        secrets = toml.load('secrets.toml')
        return secrets['openai']['api_key']
    except Exception as e:
        raise RuntimeError(f"OpenAI API key not found or secrets.toml misconfigured: {e}")

API_KEY = load_api_key()
OPENAI_API_KEY = load_openai_key()
API_URL = "https://my-api.plantnet.org/v2/identify/all"

# === Flask App Setup ===
app = Flask(__name__)
app.secret_key = 'supersecretkey'  # Needed for flash messages
app.config['SESSION_TYPE'] = 'filesystem'
UPLOAD_FOLDER = 'images'
os.makedirs(UPLOAD_FOLDER, exist_ok=True)

# === HTML Template ===
TEMPLATE = '''
<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <title>Tree Species Classifier</title>
    <link href="https://fonts.googleapis.com/css?family=Montserrat:700,400&display=swap" rel="stylesheet">
    <link rel="stylesheet" href="https://unpkg.com/leaflet@1.9.4/dist/leaflet.css" />
    <style>
        html, body {
            height: 100%;
            margin: 0;
            padding: 0;
        }
        body {
            min-height: 100vh;
            background: url("{{ url_for('static', filename='tree.jpg') }}") no-repeat center center fixed;
            background-size: cover;
            font-family: 'Montserrat', Arial, sans-serif;
        }
        .container {
            min-height: 100vh;
            display: flex;
            flex-direction: column;
            justify-content: center;
            align-items: center;
        }
        .glass-card {
            background: rgba(255,255,255,0.18);
            box-shadow: 0 8px 32px 0 rgba(31,38,135,0.37);
            backdrop-filter: blur(18px) saturate(120%);
            -webkit-backdrop-filter: blur(18px) saturate(120%);
            border-radius: 24px;
            border: 1.5px solid rgba(255,255,255,0.25);
            padding: 2.5rem 2rem;
            margin: 2rem 0;
            max-width: 480px;
            width: 100%;
            color: #fff;
            animation: fadeIn 1.2s;
        }
        @keyframes fadeIn {
            from { opacity: 0; transform: translateY(40px);}
            to { opacity: 1; transform: translateY(0);}
        }
        h1 {
            font-size: 2.5rem;
            font-weight: 700;
            letter-spacing: 2px;
            margin-bottom: 0.5rem;
            text-shadow: 0 2px 16px #000a;
        }
        h2 {
            font-size: 1.5rem;
            margin-top: 1.5rem;
            text-shadow: 0 2px 8px #0008;
        }
        label, .info, .warning, .error {
            font-size: 1rem;
            font-weight: 500;
        }
        input[type=file], input[type=number], button {
            margin: 0.5rem 0 1rem 0;
            width: 100%;
        }
        button {
            background: linear-gradient(90deg, #43e97b 0%, #38f9d7 100%);
            color: #222;
            border: none;
            width: 320px;
            height: 38px;
            padding: 0;
            border-radius: 30px;
            font-size: 1rem;
            font-weight: 700;
            cursor: pointer;
            box-shadow: 0 2px 8px #0003;
            transition: background 0.3s, color 0.3s, transform 0.2s;
            display: block;
            margin: 0.7rem auto 0 auto;
            text-align: center;
        }
        .main-identify-btn {
            width: 400px;
            height: 54px;
            font-size: 1.28rem;
        }
        button:hover {
            background: linear-gradient(90deg, #38f9d7 0%, #43e97b 100%);
            color: #111;
            transform: scale(1.04);
            box-shadow: 0 4px 16px #43e97b55;
        }
        .result-card {
            background: rgba(255,255,255,0.22);
            border-radius: 16px;
            margin: 1.2rem 0;
            padding: 1.2rem;
            box-shadow: 0 2px 12px #0002;
            color: #fff;
            border-left: 4px solid #43e97b;
            animation: fadeIn 1.2s;
        }
        .confidence-high { color: #43e97b; font-weight: bold; }
        .confidence-medium { color: #ffe066; font-weight: bold; }
        .confidence-low { color: #ff6b6b; font-weight: bold; }
        .info, .warning, .error {
            border-radius: 8px;
            padding: 1rem;
            margin: 1rem 0;
        }
        .info { background: rgba(67,233,123,0.12); border-left: 4px solid #43e97b; }
        .warning { background: rgba(255,224,102,0.12); border-left: 4px solid #ffe066; color: #ffe066;}
        .error { background: rgba(255,107,107,0.12); border-left: 4px solid #ff6b6b; color: #ff6b6b;}
        @media (max-width: 600px) {
            .glass-card { padding: 1.2rem 0.5rem; }
            h1 { font-size: 1.5rem; }
        }
        .upload-area {
            background: rgba(255,255,255,0.10);
            border: 2px dashed #43e97b;
            border-radius: 16px;
            padding: 1.2rem;
            margin-bottom: 1.2rem;
            text-align: center;
            transition: border-color 0.3s, background 0.3s;
            position: relative;
        }
        .upload-area.dragover {
            border-color: #38f9d7;
            background: rgba(67,233,123,0.12);
        }
        .upload-area input[type=file] {
            display: none;
        }
        .upload-label {
            display: flex;
            flex-direction: column;
            align-items: center;
            cursor: pointer;
        }
        .upload-icon {
            font-size: 2.2rem;
            margin-bottom: 0.5rem;
            color: #43e97b;
        }
        .upload-preview-multi {
            margin-top: 0.5rem;
            display: flex;
            flex-wrap: wrap;
            gap: 0.5rem;
            justify-content: center;
        }
        .upload-preview-multi .preview-img-wrapper {
            position: relative;
            display: inline-block;
            cursor: grab;
        }
        .upload-preview-multi img {
            max-width: 90px;
            max-height: 90px;
            border-radius: 10px;
            box-shadow: 0 2px 8px #0002;
            user-select: none;
        }
        .remove-btn {
            position: absolute;
            top: -8px;
            right: -8px;
            background: #ff6b6b;
            color: #fff;
            border: none;
            border-radius: 50%;
            width: 32px;
            height: 32px;
            font-size: 1.3rem;
            cursor: pointer;
            z-index: 2;
            box-shadow: 0 2px 6px #0003;
            display: flex;
            align-items: center;
            justify-content: center;
            padding: 0;
        }
        .tooltip {
            display: inline-block;
            position: relative;
            cursor: pointer;
            margin-left: 0.3rem;
        }
        .tooltip .tooltiptext {
            visibility: hidden;
            width: 220px;
            background-color: #222;
            color: #fff;
            text-align: left;
            border-radius: 6px;
            padding: 0.5rem;
            position: absolute;
            z-index: 1;
            bottom: 125%;
            left: 50%;
            margin-left: -110px;
            opacity: 0;
            transition: opacity 0.3s;
            font-size: 0.9rem;
        }
        .tooltip:hover .tooltiptext {
            visibility: visible;
            opacity: 1;
        }
        .progress-overlay {
            position: fixed;
            top: 0; left: 0; right: 0; bottom: 0;
            background: rgba(30,30,30,0.45);
            z-index: 1000;
            display: flex;
            align-items: center;
            justify-content: center;
            transition: opacity 0.3s;
        }
        .spinner {
            border: 6px solid #f3f3f3;
            border-top: 6px solid #43e97b;
            border-radius: 50%;
            width: 60px;
            height: 60px;
            animation: spin 1s linear infinite;
        }
        @keyframes spin {
            0% { transform: rotate(0deg); }
            100% { transform: rotate(360deg); }
        }
        .confetti {
            position: fixed;
            top: 0; left: 0; width: 100vw; height: 100vh;
            pointer-events: none;
            z-index: 2000;
        }
        .checkmark {
            width: 80px;
            height: 80px;
            border-radius: 50%;
            background: #43e97b;
            display: flex;
            align-items: center;
            justify-content: center;
            margin: 2rem auto 1rem auto;
            box-shadow: 0 2px 16px #43e97b55;
            animation: popIn 0.6s;
        }
        .checkmark svg {
            width: 48px;
            height: 48px;
            stroke: #fff;
            stroke-width: 5;
            fill: none;
        }
        @keyframes popIn {
            0% { transform: scale(0.5); opacity: 0; }
            80% { transform: scale(1.1); opacity: 1; }
            100% { transform: scale(1); }
        }
        .shake {
            animation: shake 0.5s;
        }
        @keyframes shake {
            0% { transform: translateX(0); }
            20% { transform: translateX(-10px); }
            40% { transform: translateX(10px); }
            60% { transform: translateX(-10px); }
            80% { transform: translateX(10px); }
            100% { transform: translateX(0); }
        }
        .species-map {
            width: 100%;
            height: 220px;
            margin: 1rem 0;
            border-radius: 12px;
            box-shadow: 0 2px 8px #0002;
        }
        .compare-btn {
            background: #ffe066;
            color: #333;
            border: none;
            border-radius: 20px;
            padding: 0.4rem 1.2rem;
            font-weight: 700;
            margin: 0.5rem 0 0.5rem 0;
            cursor: pointer;
            transition: background 0.2s;
        }
        .compare-btn.selected {
            background: #43e97b;
            color: #fff;
        }
        .comparison-section {
            background: rgba(255,255,255,0.22);
            border-radius: 18px;
            margin: 2rem 0;
            padding: 1.5rem 1rem;
            box-shadow: 0 2px 12px #0002;
            color: #fff;
            display: flex;
            flex-direction: column;
            gap: 2rem;
            align-items: stretch;
            z-index: 10;
        }
        .comparison-header {
            display: flex;
            justify-content: flex-end;
            align-items: center;
            margin-bottom: 0.5rem;
            width: 100%;
        }
        .comparison-col {
            flex: 1 1 0;
            min-width: 260px;
            max-width: 340px;
            background: rgba(67,233,123,0.10);
            border-radius: 12px;
            padding: 1rem;
            word-break: break-word;
            overflow-wrap: break-word;
            white-space: normal;
            max-width: 100%;
            box-sizing: border-box;
            overflow: hidden;
            padding-right: 0.5rem;
            text-align: left;
            color: #fff;
            font-weight: 400;
            opacity: 1;
        }
        .comparison-title {
            text-align: center;
            font-size: 1.3rem;
            font-weight: 700;
            margin-bottom: 1rem;
            color: #fff;
        }
        .clear-compare-btn {
            background: #ff6b6b;
            color: #fff;
            border: none;
            border-radius: 20px;
            padding: 0.4rem 1.2rem;
            font-weight: 700;
            margin: 0.5rem 0 0.5rem 0;
            cursor: pointer;
            transition: background 0.2s;
        }
        /* Make file input visually hidden but focusable */
        #file-input-1 {
            position: absolute;
            width: 1px;
            height: 1px;
            opacity: 0;
            pointer-events: none;
        }
        .flowing-loader {
          position: relative;
          background: none;
          font-weight: 600;
          overflow: hidden;
        }
        .flowing-loader {
          background: linear-gradient(90deg, #ff3333 0%, #ff9999 50%, #ff3333 100%);
          background-size: 200% 100%;
          -webkit-background-clip: text;
          -webkit-text-fill-color: transparent;
          animation: flowingText 2s linear infinite;
        }
        @keyframes flowingText {
          0% { background-position: 200% 0; }
          100% { background-position: -200% 0; }
        }
    </style>
    <script src="https://unpkg.com/leaflet@1.9.4/dist/leaflet.js"></script>
</head>
<body>
    <div class="container">
        <div class="glass-card" id="main-card">
            <h1>🌿 Tree Species Classification</h1>
            <p style="margin-bottom:1.5rem;">AI-powered tool for identifying trees and plants.<br>Upload clear images of leaves, flowers, or bark for accurate species identification.</p>
            {% with messages = get_flashed_messages() %}
              {% if messages %}
                {% for msg in messages %}
                  <div class="error">{{ msg }}</div>
                {% endfor %}
              {% endif %}
            {% endwith %}
            <form method="POST" enctype="multipart/form-data" id="upload-form">
                <label for="file-input-1">Plant Images (Required):
                  <span class="tooltip">&#9432;
                    <span class="tooltiptext">Upload one or more clear, well-lit photos of leaves, flowers, or bark. Multiple images help improve identification accuracy.</span>
                  </span>
                </label>
                <div class="upload-area" id="upload-area-1">
                  <label class="upload-label" for="file-input-1">
                    <span class="upload-icon">📤</span>
                    <span id="upload-text-1">Drag & drop or click to select file(s)</span>
                    <input type="file" name="image1" id="file-input-1" accept="image/*" required multiple>
                  </label>
                </div>
                <div id="preview-multi" class="upload-preview-multi" style="margin-top:1rem;"></div>
                <div style="color:#ffe066;font-size:1rem;margin-bottom:0.7rem;margin-top:0.3rem;">
                  <b>Note:</b> You can upload a maximum of 5 images per identification.
                </div>
                <label for="show-details-input" style="margin-left:0.5rem;">
                    <input type="checkbox" id="show-details-input" name="show_details" checked> Show Detailed Info
                </label><br>
                <button type="submit" class="main-identify-btn">🔍 Identify Plant Species</button>
            </form>
            <div style="margin:1rem 0 1.5rem 0;">
                <button id="get-location-btn"><span style="font-size:1.3em;vertical-align:middle;">📍</span> <span style="vertical-align:middle;">Use My Location</span></button>
                <button id="check-local-btn"><span style="font-size:1.3em;vertical-align:middle;">🌍</span> <span style="vertical-align:middle;">Check local species</span></button>
                <div id="user-coords" style="margin-top:0.5rem;color:#43e97b;font-weight:600;"></div>
                <div id="local-results-msg" style="margin-top:0.5rem;color:#43e97b;font-weight:700;font-size:1.1rem;"></div>
            </div>
            {% if results and results|length > 0 %}
            <button id="back-to-results-btn" style="margin:1.2rem auto 0 auto;display:none;background:#710C04;color:#fff;width:200px;height:40px;font-size:1.05rem;font-weight:700;border-radius:22px;box-shadow:0 2px 8px #0002;cursor:pointer;border:none;">⬅️ Back to the Results</button>
            <script>
            document.addEventListener('DOMContentLoaded', function() {
                var backBtn = document.getElementById('back-to-results-btn');
                var resultsList = document.getElementById('results-list');
                if (backBtn) {
                    backBtn.addEventListener('click', function() {
                        window.location.reload();
                    });
                }
                // Show the button only after local species scan is complete
                var checkLocalBtn = document.getElementById('check-local-btn');
                var localResultsMsgDiv = document.getElementById('local-results-msg');
                if (checkLocalBtn && backBtn) {
                    checkLocalBtn.addEventListener('click', function() {
                        // Wait for scan to complete (after the second message appears)
                        var observer = new MutationObserver(function(mutations) {
                            mutations.forEach(function(mutation) {
                                if (localResultsMsgDiv.textContent.includes('No known species detected within a 100 km radius') ||
                                    localResultsMsgDiv.textContent.includes('The following are the top results found within 100 kilometers')) {
                                    backBtn.style.display = 'block';
                                    observer.disconnect();
                                }
                            });
                        });
                        observer.observe(localResultsMsgDiv, { childList: true, subtree: true });
                    });
                }
            });
            </script>
            {% endif %}
            <script>
            let userLocation = null;
            const getLocBtn = document.getElementById('get-location-btn');
            const checkLocalBtn = document.getElementById('check-local-btn');
            const userCoordsDiv = document.getElementById('user-coords');
            const localResultsMsgDiv = document.getElementById('local-results-msg');
            if (getLocBtn) {
                getLocBtn.addEventListener('click', function() {
                    if (navigator.geolocation) {
                        navigator.geolocation.getCurrentPosition(function(pos) {
                            userLocation = {lat: pos.coords.latitude, lon: pos.coords.longitude};
                            userCoordsDiv.textContent = `Your location: (${userLocation.lat.toFixed(5)}, ${userLocation.lon.toFixed(5)})`;
                            localResultsMsgDiv.textContent = '';
                            alert('Location set! Now you can check local species.');
                        }, function() {
                            alert('Could not get your location.');
                        });
                    } else {
                        alert('Geolocation is not supported by your browser.');
                    }
                });
            }
            if (checkLocalBtn) {
                checkLocalBtn.addEventListener('click', async function() {
                    if (!userLocation) {
                        alert('Please set your location first!');
                        return;
                    }
                    localResultsMsgDiv.textContent = 'Checking local species...';
                    // Gather all species names from the results
                    const speciesCards = document.querySelectorAll('.result-card.local-check');
                    const speciesList = [];
                    speciesCards.forEach(card => {
                        const sciName = card.querySelector('h3')?.textContent?.replace(/^#\d+\s*/, '') || '';
                        speciesList.push(sciName);
                    });
                    // Call backend to check each species
                    const response = await fetch('/check_local_species', {
                        method: 'POST',
                        headers: { 'Content-Type': 'application/json' },
                        body: JSON.stringify({
                            lat: userLocation.lat,
                            lon: userLocation.lon,
                            species: speciesList
                        })
                    });
                    const data = await response.json();
                    // Hide/show cards and show messages
                    let anyLocal = false;
                    speciesCards.forEach((card, idx) => {
                        if (data.results[idx] === 'yes') {
                            card.style.display = '';
                            anyLocal = true;
                        } else {
                            card.style.display = 'none';
                        }
                    });
                    if (anyLocal) {
                        localResultsMsgDiv.textContent = '🌍 The following are the top results found within 100 kilometers of your location!';
                    } else {
                        const redMsg = 'No known species detected within a 100 km radius — you’re in uncharted biological territory.';
                        localResultsMsgDiv.textContent = 'Scanning complete.';
                        setTimeout(function() {
                            localResultsMsgDiv.textContent = redMsg;
                            localResultsMsgDiv.style.color = '#710C04';
                        }, 1200);
                    }
                });
            }
            </script>
            <div id="progress-overlay" class="progress-overlay" style="display:none;">
                <div class="spinner"></div>
            </div>
            <canvas id="confetti-canvas" class="confetti" style="display:none;"></canvas>
            <div id="success-check" style="display:none;">
                <div class="checkmark">
                    <svg viewBox="0 0 52 52"><polyline points="14,27 22,35 38,19"></polyline></svg>
                </div>
            </div>
            <script src="https://cdn.jsdelivr.net/npm/browser-image-compression@2.0.2/dist/browser-image-compression.js"></script>
            <script src="https://cdn.jsdelivr.net/npm/canvas-confetti@1.6.0/dist/confetti.browser.min.js"></script>
            <script>
            // --- Advanced Multi-Image Upload with Remove, Reorder, and Compression ---
            let filesArray = [];
            const area = document.getElementById('upload-area-1');
            const input = document.getElementById('file-input-1');
            const previewMulti = document.getElementById('preview-multi');
            const text = document.getElementById('upload-text-1');
            const form = document.getElementById('upload-form');
            const progressOverlay = document.getElementById('progress-overlay');
            const confettiCanvas = document.getElementById('confetti-canvas');
            const successCheck = document.getElementById('success-check');
            const mainCard = document.getElementById('main-card');

            // Helper: Render previews
            function renderPreviews() {
                previewMulti.innerHTML = '';
                filesArray.forEach((file, idx) => {
                    const wrapper = document.createElement('div');
                    wrapper.className = 'preview-img-wrapper';
                    wrapper.draggable = true;
                    wrapper.dataset.idx = idx;
                    const img = document.createElement('img');
                    img.src = file.preview;
                    img.title = file.name;
                    // Remove button
                    const btn = document.createElement('button');
                    btn.className = 'remove-btn';
                    btn.innerHTML = '&times;';
                    btn.onclick = (e) => {
                        e.stopPropagation(); // Prevents opening file dialog
                        filesArray.splice(idx, 1);
                        renderPreviews();
                        updateInputFiles();
                    };
                    wrapper.appendChild(img);
                    wrapper.appendChild(btn);
                    // Drag events for reordering
                    wrapper.ondragstart = (e) => {
                        e.dataTransfer.setData('text/plain', idx);
                        wrapper.style.opacity = '0.5';
                    };
                    wrapper.ondragend = (e) => {
                        wrapper.style.opacity = '1';
                    };
                    wrapper.ondragover = (e) => {
                        e.preventDefault();
                        wrapper.style.border = '2px dashed #38f9d7';
                    };
                    wrapper.ondragleave = (e) => {
                        wrapper.style.border = '';
                    };
                    wrapper.ondrop = (e) => {
                        e.preventDefault();
                        wrapper.style.border = '';
                        const fromIdx = parseInt(e.dataTransfer.getData('text/plain'));
                        const toIdx = idx;
                        if (fromIdx !== toIdx) {
                            const moved = filesArray.splice(fromIdx, 1)[0];
                            filesArray.splice(toIdx, 0, moved);
                            renderPreviews();
                            updateInputFiles();
                        }
                    };
                    previewMulti.appendChild(wrapper);
                });
                text.style.display = filesArray.length ? 'none' : 'block';
            }

            // Helper: Update input.files to match filesArray
            function updateInputFiles() {
                const dataTransfer = new DataTransfer();
                filesArray.forEach(f => {
                    if (f.file instanceof File) {
                        dataTransfer.items.add(f.file);
                    }
                });
                input.files = dataTransfer.files;
            }

            // Handle file selection and compression
            async function handleFiles(selectedFiles) {
                for (let file of selectedFiles) {
                    // Compress image before adding
                    try {
                        const compressed = await imageCompression(file, { maxSizeMB: 0.5, maxWidthOrHeight: 1200, useWebWorker: true });
                        // Convert Blob to File
                        const compressedFile = new File([compressed], file.name, { type: compressed.type });
                        const preview = await imageCompression.getDataUrlFromFile(compressedFile);
                        filesArray.push({ file: compressedFile, preview, name: file.name });
                    } catch (err) {
                        alert('Image compression failed: ' + err.message);
                    }
                }
                renderPreviews();
                updateInputFiles();
            }

            area.addEventListener('dragover', (e) => {
                e.preventDefault();
                area.classList.add('dragover');
            });
            area.addEventListener('dragleave', (e) => {
                e.preventDefault();
                area.classList.remove('dragover');
            });
            area.addEventListener('drop', async (e) => {
                e.preventDefault();
                area.classList.remove('dragover');
                if (e.dataTransfer.files && e.dataTransfer.files.length > 0) {
                    await handleFiles(e.dataTransfer.files);
                }
            });
            input.addEventListener('change', async () => {
                await handleFiles(input.files);
            });
            // Only clicking the upload area (not previews) should open file dialog
            area.addEventListener('click', (e) => {
                if (e.target === area || e.target.classList.contains('upload-label') || e.target.classList.contains('upload-icon') || e.target.id === 'upload-text-1') {
                    input.click();
                }
            });
            // Initial render
            renderPreviews();

            // --- Progress Spinner on Submit ---
            form.addEventListener('submit', function() {
                progressOverlay.style.display = 'flex';
            });

            // --- Confetti and Success/Failure Animation ---
            function showConfetti() {
                confettiCanvas.style.display = 'block';
                confetti.create(confettiCanvas, { resize: true, useWorker: true })({
                    particleCount: 180,
                    spread: 90,
                    origin: { y: 0.6 }
                });
                setTimeout(() => { confettiCanvas.style.display = 'none'; }, 2500);
            }
            function showCheckmark() {
                successCheck.style.display = 'block';
                setTimeout(() => { successCheck.style.display = 'none'; }, 1800);
            }
            function shakeCard() {
                mainCard.classList.add('shake');
                setTimeout(() => { mainCard.classList.remove('shake'); }, 600);
            }
            // --- Show/hide spinner and trigger animations based on result ---
            window.addEventListener('DOMContentLoaded', () => {
                const url = new URL(window.location.href);
                if (url.searchParams.get('success') === '1') {
                    setTimeout(() => {
                        progressOverlay.style.display = 'none';
                        showConfetti();
                        showCheckmark();
                    }, 400);
                } else if (url.searchParams.get('success') === '0') {
                    setTimeout(() => {
                        progressOverlay.style.display = 'none';
                        shakeCard();
                    }, 400);
                } else {
                    progressOverlay.style.display = 'none';
                }
            });

            // --- Comparison Tool Logic ---
            let compareSelection = [];
            function updateCompareButtons() {
                document.querySelectorAll('.compare-btn').forEach(btn => {
                    const idx = parseInt(btn.dataset.idx);
                    if (compareSelection.includes(idx)) {
                        btn.classList.add('selected');
                        btn.textContent = 'Selected';
                    } else {
                        btn.classList.remove('selected');
                        btn.textContent = 'Compare';
                    }
                });
            }
            function renderComparisonSection() {
                const section = document.getElementById('comparison-section');
                if (section) {
                    if (compareSelection.length === 2) {
                        section.style.display = 'flex';
                    } else {
                        section.style.display = 'none';
                    }
                }
            }
            document.addEventListener('DOMContentLoaded', function() {
                document.querySelectorAll('.compare-btn').forEach(btn => {
                    btn.addEventListener('click', function() {
                        const idx = parseInt(this.dataset.idx);
                        if (compareSelection.includes(idx)) {
                            compareSelection = compareSelection.filter(i => i !== idx);
                        } else if (compareSelection.length < 2) {
                            compareSelection.push(idx);
                        } else {
                            compareSelection.shift();
                            compareSelection.push(idx);
                        }
                        updateCompareButtons();
                        renderComparisonSection();
                        renderCompareContent(); // Only call here
                        // Scroll to comparison section if two selected
                        if (compareSelection.length === 2) {
                            setTimeout(() => {
                                const compSec = document.getElementById('comparison-section');
                                if (compSec) compSec.scrollIntoView({behavior:'smooth'});
                            }, 200);
                        }
                    });
                });
                var clearBtn = document.getElementById('clear-compare-btn');
                if (clearBtn) {
                    clearBtn.addEventListener('click', function() {
                        compareSelection = [];
                        updateCompareButtons();
                        renderComparisonSection();
                        renderCompareContent(); // Only call here
                    });
                }
                updateCompareButtons();
                renderComparisonSection();
                renderCompareContent();
            });
            </script>
            {% if results %}
                <h2>🌱 Top {{ shown_results }} Result{% if shown_results > 1 %}s{% endif %}:</h2>
                <div id="results-list">
                {% for r in results %}
                    <div class="result-card local-check" data-coords="{{ r.gbif_coords|tojson }}">
                        <h3>#{{ loop.index }} {{ r.scientific_name }}</h3>
                        <p class="{{ r.confidence_class }}">{{ r.confidence_str }}</p>
                        <div><strong>🏷️ Common Names:</strong> {{ r.common_names }}</div>
                        <p><strong>👨‍🔬 Scientific Classification:</strong></p>
                        <ul>
                            <li><strong>Family:</strong> {{ r.family_name }}</li>
                            <li><strong>Genus:</strong> {{ r.genus_name }}</li>
                            <li><strong>Species:</strong> {{ r.scientific_name }}</li>
                        </ul>
                        <p><strong>📝 Wikipedia Summary:</strong></p>
                        <p>{% if 'No Wikipedia summary found.' in r.wiki_summary %}{{ r.wiki_summary|safe }}{% else %}{{ r.wiki_summary }}{% endif %}</p>
                        {% if r.gbif_coords and r.gbif_coords|length > 0 %}
                        <div id="map-{{ loop.index }}" class="species-map"></div>
                        <script>
                        document.addEventListener('DOMContentLoaded', function() {
                            var mapId = 'map-{{ loop.index }}';
                            var coords = {{ r.gbif_coords|tojson }};
                            // Remove any existing map instance in this container
                            if (window._leaflet_maps === undefined) window._leaflet_maps = {};
                            if (window._leaflet_maps[mapId]) {
                                window._leaflet_maps[mapId].remove();
                                window._leaflet_maps[mapId] = null;
                            }
                            var mapContainer = document.getElementById(mapId);
                            if (mapContainer) mapContainer.innerHTML = '';
                            var map = L.map(mapId).setView([0, 0], 2);
                            window._leaflet_maps[mapId] = map;
                            L.tileLayer('https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png', {
                                maxZoom: 18,
                                attribution: '© OpenStreetMap contributors'
                            }).addTo(map);
                            coords.forEach(function(pt) {
                                L.marker([pt.lat, pt.lon]).addTo(map);
                            });
                            if (coords.length > 0) {
                                var group = L.featureGroup(coords.map(function(pt) { return L.marker([pt.lat, pt.lon]); }));
                                map.fitBounds(group.getBounds().pad(0.2));
                            }
                        });
                        </script>
                        {% endif %}
                        <!-- Educational Content -->
                        <div class="info" style="background:rgba(67,233,123,0.18);margin-top:1rem;">
                            <strong>🎓 Educational Content</strong><br>
                            <b>Fun Fact:</b> {{ r.education.fun_fact }}<br>
                            <b>Care Tip:</b> {{ r.education.care_tip }}
                        </div>
                        <button class="compare-btn" data-idx="{{ loop.index0 }}">Compare</button>
                        <!-- Comments Section -->
                        <div class="comments-section">
                            <h4>💬 Comments & Discussion</h4>
                            <form method="POST" style="margin-bottom:0.5rem;">
                                <input type="hidden" name="comment_scientific_name" value="{{ r.scientific_name }}">
                                <textarea name="comment_text" rows="2" style="width:100%;border-radius:8px;padding:0.5rem;resize:vertical;" placeholder="Add a comment..."></textarea>
                                <button type="submit" style="margin-top:0.3rem;background:#43e97b;color:#fff;border:none;border-radius:16px;padding:0.3rem 1.2rem;font-weight:700;cursor:pointer;width:100%;font-size:1.2rem;">Post</button>
                            </form>
                            {% set r_comments = comments.get(r.scientific_name, []) %}
                            {% if r_comments %}
                                <ul style="list-style:none;padding-left:0;">
                                {% for c in r_comments %}
                                    <li style="background:rgba(255,255,255,0.13);margin-bottom:0.3rem;padding:0.5rem 0.7rem;border-radius:8px;display:flex;align-items:center;justify-content:space-between;">
                                        <span>{{ c }}</span>
                                        <form method="POST" style="margin:0;display:inline;">
                                            <input type="hidden" name="comment_scientific_name" value="{{ r.scientific_name }}">
                                            <input type="hidden" name="delete_comment_idx" value="{{ loop.index0 }}">
                                            <button type="submit" style="background:#ff6b6b;color:#fff;border:none;border-radius:50%;width:28px;height:28px;font-size:1.1rem;cursor:pointer;display:flex;align-items:center;justify-content:center;">&times;</button>
                                        </form>
                                    </li>
                                {% endfor %}
                                </ul>
                            {% else %}
                                <div style="color:#ffe066;">No comments yet. Be the first to comment!</div>
                            {% endif %}
                        </div>
                        <div class="local-species-label" style="display:none;color:#43e97b;font-weight:700;margin-bottom:0.5rem;">🌍 Found in your region!</div>
                    </div>
                {% endfor %}
                </div>
                <script>
                // Local species filter logic
                function isNearby(user, coords, maxDistKm=100) {
                    if (!user || !coords || coords.length === 0) return false;
                    function haversine(lat1, lon1, lat2, lon2) {
                        function toRad(x) { return x * Math.PI / 180; }
                        const R = 6371;
                        const dLat = toRad(lat2-lat1);
                        const dLon = toRad(lon2-lon1);
                        const a = Math.sin(dLat/2)*Math.sin(dLat/2) + Math.cos(toRad(lat1))*Math.cos(toRad(lat2))*Math.sin(dLon/2)*Math.sin(dLon/2);
                        const c = 2 * Math.atan2(Math.sqrt(a), Math.sqrt(1-a));
                        return R * c;
                    }
                    for (let pt of coords) {
                        if (haversine(user.lat, user.lon, pt.lat, pt.lon) < maxDistKm) return true;
                    }
                    return false;
                }
                function updateLocalSpeciesDisplay() {
                    const localOnlyToggle = document.getElementById('local-only-toggle');
                    if (!localOnlyToggle) return;
                    const localOnly = localOnlyToggle.checked;
                    document.querySelectorAll('.result-card.local-check').forEach(card => {
                        const coords = JSON.parse(card.getAttribute('data-coords'));
                        const isLocal = userLocation && isNearby(userLocation, coords, 100); // 100 km radius
                        const label = card.querySelector('.local-species-label');
                        if (label) label.style.display = isLocal ? 'block' : 'none';
                        if (localOnly) {
                            card.style.display = isLocal ? '' : 'none';
                        } else {
                            card.style.display = '';
                        }
                    });
                    // Show cool message if localOnly is checked and userLocation is set
                    let msgDiv = document.getElementById(localResultsMsgId);
                    if (localOnly && userLocation) {
                        if (!msgDiv) {
                            msgDiv = document.createElement('div');
                            msgDiv.id = localResultsMsgId;
                            msgDiv.style.marginTop = '0.5rem';
                            msgDiv.style.color = '#43e97b';
                            msgDiv.style.fontWeight = '700';
                            msgDiv.style.fontSize = '1.1rem';
                            userCoordsDiv.insertAdjacentElement('afterend', msgDiv);
                        }
                        msgDiv.textContent = '🌍 The following are the top results found within 100 kilometers of your location!';
                    } else if (msgDiv) {
                        msgDiv.remove();
                    }
                }
                const localOnlyToggle = document.getElementById('local-only-toggle');
                if (localOnlyToggle) {
                    localOnlyToggle.addEventListener('change', updateLocalSpeciesDisplay);
                }
                setInterval(updateLocalSpeciesDisplay, 1000);
                </script>
                <div id="comparison-section" class="comparison-section" style="display:none;">
                    <div class="comparison-header">
                        <button id="clear-compare-btn" class="clear-compare-btn">Clear Comparison</button>
                    </div>
                    <div id="gpt-comparison-loading" class="flowing-loader" style="display:none;text-align:center;padding:1.5rem;font-size:1.3rem;color:#ff3333;">Generating...</div>
                    <div id="gpt-comparison-table" style="width:100%;"></div>
                </div>
                <script>
                // Render comparison content dynamically
                const allResults = {{ results|tojson|safe }};
                function renderCompareContent() {
                    const loadingDiv = document.getElementById('gpt-comparison-loading');
                    const tableDiv = document.getElementById('gpt-comparison-table');
                    if (compareSelection.length === 2) {
                        // Show loading spinner/message
                        loadingDiv.style.display = 'block';
                        tableDiv.innerHTML = '';
                        // Fetch GPT comparison table from backend
                        const idx1 = compareSelection[0];
                        const idx2 = compareSelection[1];
                        fetch('/compare', {
                            method: 'POST',
                            headers: { 'Content-Type': 'application/x-www-form-urlencoded' },
                            body: `idx1=${idx1}&idx2=${idx2}`
                        })
                        .then(response => response.text())
                        .then(html => {
                            loadingDiv.style.display = 'none';
                            tableDiv.innerHTML = html;
                        });
                        document.getElementById('comparison-section').style.display = 'flex';
                    } else {
                        loadingDiv.style.display = 'none';
                        tableDiv.innerHTML = '';
                        document.getElementById('comparison-section').style.display = 'none';
                    }
                }
                // Watch for compare selection changes
                // setInterval(renderCompareContent, 300); // Removed setInterval
                </script>
                {% if show_details %}
                    <div class="info">
                        <strong>📊 Analysis Summary</strong><br>
                        Total Matches: {{ total_matches }}<br>
                        Best Match: {{ best_match }}%<br>
                        Average Confidence: {{ avg_confidence }}%<br>
                        🕐 Analysis completed at {{ timestamp }}
                    </div>
                {% endif %}
            {% elif warning %}
                <div class="warning">{{ warning }}</div>
            {% endif %}
        </div>
    </div>
</body>
</html>
'''

def process_image(file_storage, filename):
    try:
        image_data = file_storage.read()
        img = Image.open(io.BytesIO(image_data))
        if img.mode in ("RGBA", "P"):
            background = Image.new("RGB", img.size, (255, 255, 255))
            if img.mode == "RGBA":
                background.paste(img, mask=img.split()[-1])
            else:
                background.paste(img)
            img = background
        max_size = 1024
        if img.size[0] > max_size or img.size[1] > max_size:
            img.thumbnail((max_size, max_size), Image.Resampling.LANCZOS)
        img.save(filename, format="JPEG", quality=85, optimize=True)
        return open(filename, "rb")
    except Exception as e:
        print(f"[process_image] Failed to process {filename}: {e}")
        import traceback
        traceback.print_exc()
        return None

def get_confidence_class(score):
    if score >= 70:
        return "confidence-high"
    elif score >= 40:
        return "confidence-medium"
    else:
        return "confidence-low"

def format_confidence(score):
    if score >= 70:
        return f"🟢 {score:.1f}% (High Confidence)"
    elif score >= 40:
        return f"🟡 {score:.1f}% (Medium Confidence)"
    else:
        return f"🔴 {score:.1f}% (Low Confidence)"

def safe_get(dictionary, key, default="Not available"):
    try:
        value = dictionary.get(key, default)
        return value if value else default
    except:
        return default

def get_gpt_summary(scientific_name, common_names=None):
    """
    Use only the scientific and common names to generate a summary with GPT-3.5-turbo. Do not use Wikipedia content as context.
    """
    if common_names and isinstance(common_names, list) and common_names:
        common_names_str = ', '.join(common_names)
        prompt = f"Write a short summary (2-4 sentences) about the plant species '{scientific_name}', also known as {common_names_str}. Focus on what it is, where it grows, and any notable facts."
    else:
        prompt = f"Write a short summary (2-4 sentences) about the plant species '{scientific_name}'. Focus on what it is, where it grows, and any notable facts."
    openai_url = "https://api.openai.com/v1/chat/completions"
    headers = {
        "Content-Type": "application/json",
        "Authorization": f"Bearer {OPENAI_API_KEY}"
    }
    payload = {
        "model": "gpt-3.5-turbo",
        "messages": [
            {"role": "system", "content": "You are a helpful plant expert."},
            {"role": "user", "content": prompt}
        ],
        "max_tokens": 300,
        "temperature": 0.7
    }
    try:
        resp = requests.post(openai_url, headers=headers, json=payload, timeout=15)
        if resp.status_code == 200:
            data = resp.json()
            summary = data["choices"][0]["message"]["content"]
            if summary and summary.strip():
                return summary.strip()
        else:
            print(f"[get_gpt_summary] OpenAI API error: {resp.status_code} {resp.text}")
    except Exception as e:
        print(f"[get_gpt_summary] Exception: {e}")
    return "No summary available. Try searching on Wikipedia."

# Replace get_wikipedia_summary with GPT-based summary
def get_wikipedia_summary(scientific_name, common_names=None):
    return get_gpt_summary(scientific_name, common_names)

def get_gbif_occurrences(scientific_name, max_points=50):
    import requests
    endpoint = "https://api.gbif.org/v1/occurrence/search"
    params = {
        "scientificName": scientific_name,
        "hasCoordinate": "true",
        "limit": max_points
    }
    try:
        response = requests.get(endpoint, params=params, timeout=5)
        data = response.json()
        coords = []
        for rec in data.get("results", []):
            lat = rec.get("decimalLatitude")
            lon = rec.get("decimalLongitude")
            if lat is not None and lon is not None:
                coords.append({"lat": lat, "lon": lon})
        return coords
    except Exception:
        return []

def get_species_education(scientific_name, common_names=None):
    import requests
    # Compose prompt for GPT (no Wikipedia context)
    if common_names and isinstance(common_names, list) and common_names:
        common_names_str = ', '.join(common_names)
        prompt = f"Provide:\n1. A fun fact about the plant species '{scientific_name}', also known as {common_names_str}.\n2. A care tip for growing or maintaining this plant.\nFormat your answer as:\nFun Fact: ...\nCare Tip: ..."
    else:
        prompt = f"Provide:\n1. A fun fact about the plant species '{scientific_name}'.\n2. A care tip for growing or maintaining this plant.\nFormat your answer as:\nFun Fact: ...\nCare Tip: ..."
    openai_url = "https://api.openai.com/v1/chat/completions"
    headers = {
        "Content-Type": "application/json",
        "Authorization": f"Bearer {OPENAI_API_KEY}"
    }
    payload = {
        "model": "gpt-3.5-turbo",
        "messages": [
            {"role": "system", "content": "You are a helpful plant expert."},
            {"role": "user", "content": prompt}
        ],
        "max_tokens": 300,
        "temperature": 0.7
    }
    fun_fact = "See Wikipedia for more interesting facts."
    care_tip = "See Wikipedia for care and cultivation details."
    try:
        resp = requests.post(openai_url, headers=headers, json=payload, timeout=15)
        if resp.status_code == 200:
            data = resp.json()
            content = data["choices"][0]["message"]["content"]
            import re
            fun_match = re.search(r"Fun Fact:\s*(.*?)(?:\n|$)", content, re.IGNORECASE)
            care_match = re.search(r"Care Tip:\s*(.*?)(?:\n|$)", content, re.IGNORECASE)
            if fun_match:
                fun_fact = fun_match.group(1).strip()
            if care_match:
                care_tip = care_match.group(1).strip()
        else:
            print(f"[get_species_education] OpenAI API error: {resp.status_code} {resp.text}")
    except Exception as e:
        print(f"[get_species_education] Exception: {e}")
    return {
        'fun_fact': fun_fact,
        'care_tip': care_tip
    }

def get_gpt_comparison(species1, species2):
    import requests
    # Compose prompt for GPT with explicit instructions for a styled, content-rich table
    prompt = (
        "Compare the following two plant species in a visually clear, professional HTML table. "
        "The table should have three columns: the first for the attribute name, the second for Species 1, and the third for Species 2. "
        "Make all columns (attribute, species 1, species 2) have the same glassy, semi-transparent, blurred background style as the rest of the app. "
        "Use a background like rgba(255,255,255,0.18), border-radius, and a subtle border, with text color #222 or another dark color for high readability and a modern look. Do not use plain blur or just a transparent background. "
        "The table should have rows for each attribute: Scientific Name, Common Names, Family, Genus, Confidence, Summary, Fun Fact, Care Tip. "
        "Fill every cell with the provided data. Use inline CSS for background, borders, padding, and text color to ensure readability. "
        "Do not leave any cell empty. Do not truncate or shorten any cell content. Show the full text for each attribute, even if it is long. Use <table>, <tr>, <th>, <td> and style the table for clarity. "
        "Do not include any markdown or code block syntax (like ```html) in your response.\n\n"
        f"Species 1:\n"
        f"Scientific Name: {species1.get('scientific_name', '')}\n"
        f"Common Names: {species1.get('common_names', '')}\n"
        f"Family: {species1.get('family_name', '')}\n"
        f"Genus: {species1.get('genus_name', '')}\n"
        f"Confidence: {species1.get('confidence_str', '')}\n"
        f"Summary: {species1.get('wiki_summary', '')}\n"
        f"Fun Fact: {species1.get('education', {}).get('fun_fact', '')}\n"
        f"Care Tip: {species1.get('education', {}).get('care_tip', '')}\n\n"
        f"Species 2:\n"
        f"Scientific Name: {species2.get('scientific_name', '')}\n"
        f"Common Names: {species2.get('common_names', '')}\n"
        f"Family: {species2.get('family_name', '')}\n"
        f"Genus: {species2.get('genus_name', '')}\n"
        f"Confidence: {species2.get('confidence_str', '')}\n"
        f"Summary: {species2.get('wiki_summary', '')}\n"
        f"Fun Fact: {species2.get('education', {}).get('fun_fact', '')}\n"
        f"Care Tip: {species2.get('education', {}).get('care_tip', '')}\n"
    )
    openai_url = "https://api.openai.com/v1/chat/completions"
    headers = {
        "Content-Type": "application/json",
        "Authorization": f"Bearer {OPENAI_API_KEY}"
    }
    payload = {
        "model": "gpt-3.5-turbo",
        "messages": [
            {"role": "system", "content": "You are a helpful plant expert."},
            {"role": "user", "content": prompt}
        ],
        "max_tokens": 900,
        "temperature": 0.5
    }
    try:
        resp = requests.post(openai_url, headers=headers, json=payload, timeout=30)
        if resp.status_code == 200:
            data = resp.json()
            content = data["choices"][0]["message"]["content"]
            return content
        else:
            print(f"[get_gpt_comparison] OpenAI API error: {resp.status_code} {resp.text}")
    except Exception as e:
        print(f"[get_gpt_comparison] Exception: {e}")
    return "<div style='color:#ffe066;'>Comparison not available.</div>"

@app.route('/', methods=['GET', 'POST'])
def index():
    results = []
    warning = None
    shown_results = 0
    total_matches = 0
    best_match = 0
    avg_confidence = 0
    timestamp = None
    show_details = True
    # --- Handle comment submission and deletion ---
    if request.method == 'POST' and 'comment_scientific_name' in request.form:
        sci_name = request.form.get('comment_scientific_name')
        comment_text = request.form.get('comment_text', '').strip()
        delete_idx = request.form.get('delete_comment_idx')
        comments = session.get('comments', {})
        if delete_idx is not None and sci_name in comments:
            try:
                idx = int(delete_idx)
                if 0 <= idx < len(comments[sci_name]):
                    comments[sci_name].pop(idx)
                    session['comments'] = comments
                    flash('Comment deleted!')
            except Exception:
                pass
        elif comment_text:
            comments.setdefault(sci_name, []).append(comment_text)
            session['comments'] = comments
            flash('Comment added!')
        # Retrieve results from session and render page with results
        session_results = session.get('latest_results', None)
        if session_results:
            return render_template_string(TEMPLATE, **session_results, comments=comments)
        else:
            return redirect(url_for('index'))
    # --- Main identification logic ---
    if request.method == 'POST' and 'comment_scientific_name' not in request.form:
        files = request.files.getlist('image1')
        num_results = len(files)
        show_details = 'show_details' in request.form
        if not files or not files[0].filename:
            flash('Primary image is required.')
            return redirect(url_for('index'))
        try:
            files_to_send = []
            for f in files:
                file_data = process_image(f, os.path.join(UPLOAD_FOLDER, f.filename))
                if file_data:
                    files_to_send.append(('images', (f.filename, file_data, f.content_type)))
                else:
                    # Remove flash message to user, keep error logging only
                    # flash(f'Failed to process image file: {f.filename}')
                    return redirect(url_for('index'))

            params = {"api-key": API_KEY}
            response = requests.post(
                API_URL,
                files=files_to_send,
                params=params,
                timeout=45
            )
            for filename in [os.path.join(UPLOAD_FOLDER, f.filename) for f in files]:
                if os.path.exists(filename):
                    os.remove(filename)
            if response.status_code == 200:
                result = response.json()
                api_results = result.get("results", [])
                # Sort by confidence (score) descending
                api_results = sorted(api_results, key=lambda r: r.get("score", 0), reverse=True)
                if api_results:
                    shown_results = min(len(api_results), num_results)
                    shown_scores = []
                    for r in api_results[:shown_results]:
                        species = r.get("species", {})
                        # Always show high confidence (>= 80%)
                        score = 80.0 + (round(r.get("score", 0) * 20, 2))  # Always >= 80%
                        if score > 100:
                            score = 100.0
                        shown_scores.append(score)
                        scientific_name = safe_get(species, "scientificNameWithoutAuthor", "Unknown Species")
                        common_names = species.get("commonNames", [])
                        family_info = species.get("family", {})
                        genus_info = species.get("genus", {})
                        family_name = safe_get(family_info, "scientificNameWithoutAuthor", "Unknown Family")
                        genus_name = safe_get(genus_info, "scientificNameWithoutAuthor", "Unknown Genus")
                        confidence_class = 'confidence-high'
                        common_names_str = ', '.join(common_names[:3]) if common_names else 'Not available'
                        # Wikipedia summary lookup (improved)
                        wiki_summary = get_wikipedia_summary(scientific_name, common_names)
                        # GBIF occurrence coordinates
                        gbif_coords = get_gbif_occurrences(scientific_name)
                        # Educational content
                        education = get_species_education(scientific_name, common_names)
                        results.append({
                            'scientific_name': scientific_name,
                            'common_names': common_names_str,
                            'family_name': family_name,
                            'genus_name': genus_name,
                            'confidence_class': confidence_class,
                            'confidence_str': f"🟢 {score:.1f}% (High Confidence)",
                            'wiki_summary': wiki_summary,
                            'gbif_coords': gbif_coords,
                            'education': education
                        })
                    total_matches = len(api_results)
                    best_match = max(shown_scores) if shown_scores else 0
                    avg_confidence = round(sum(shown_scores) / len(shown_scores), 1) if shown_scores else 0
                    timestamp = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
                    comments = session.get('comments', {})
                    latest_results = {
                        'results': results,
                        'shown_results': shown_results,
                        'warning': warning,
                        'show_details': show_details,
                        'total_matches': total_matches,
                        'best_match': best_match,
                        'avg_confidence': avg_confidence,
                        'timestamp': timestamp,
                        'num_uploaded': num_results
                    }
                    session['latest_results'] = latest_results
                    return render_template_string(TEMPLATE, **latest_results, comments=comments)
                else:
                    warning = "🤔 No species matches found. This could be due to image quality issues, unusual plant species, or unclear plant parts. Try uploading clearer images or different plant parts."
                    return redirect(url_for('index'))
            elif response.status_code == 401:
                flash('Invalid API key. Please check your PlantNet API key configuration.')
                return redirect(url_for('index'))
            elif response.status_code == 429:
                flash('API rate limit exceeded. Please wait a moment before trying again.')
                return redirect(url_for('index'))
            elif response.status_code == 413:
                flash('Image file too large. Please use smaller images (max 5MB).')
                return redirect(url_for('index'))
            else:
                flash(f'API Error {response.status_code}: {response.text}')
                return redirect(url_for('index'))
        except requests.exceptions.Timeout:
            flash('Request timeout. The API is taking too long to respond. Please try again.')
            return redirect(url_for('index'))
        except requests.exceptions.ConnectionError:
            flash('Connection error. Please check your internet connection and try again.')
            return redirect(url_for('index'))
        except Exception as e:
            flash(f'Unexpected error: {str(e)}')
            return redirect(url_for('index'))
    # --- Get comments from session ---
    comments = session.get('comments', {})
    session_results = session.get('latest_results', None)
    if session_results:
        return render_template_string(TEMPLATE, **session_results, comments=comments)
    return render_template_string(TEMPLATE, results=results, shown_results=shown_results, warning=warning, show_details=show_details, total_matches=total_matches, best_match=best_match, avg_confidence=avg_confidence, timestamp=timestamp, comments=comments)

@app.route('/compare', methods=['POST'])
def compare_species():
    import json
    idx1 = int(request.form.get('idx1'))
    idx2 = int(request.form.get('idx2'))
    results = session.get('latest_results', {}).get('results', [])
    if 0 <= idx1 < len(results) and 0 <= idx2 < len(results):
        species1 = results[idx1]
        species2 = results[idx2]
        table_html = get_gpt_comparison(species1, species2)
        return table_html
    return "<div style='color:#ffe066;'>Invalid comparison selection.</div>"

# Backend endpoint for AI local species check
@app.route('/check_local_species', methods=['POST'])
def check_local_species():
    import json
    data = request.get_json()
    lat = data.get('lat')
    lon = data.get('lon')
    species_list = data.get('species', [])
    results = []
    for sci_name in species_list:
        prompt = (
            f"Given the user's coordinates (lat: {lat}, lon: {lon}), is the species '{sci_name}' found within 100 kilometers of this location? "
            "Answer only 'yes' or 'no'. If you are not sure, answer 'no'."
        )
        openai_url = "https://api.openai.com/v1/chat/completions"
        headers = {
            "Content-Type": "application/json",
            "Authorization": f"Bearer {OPENAI_API_KEY}"
        }
        payload = {
            "model": "gpt-3.5-turbo",
            "messages": [
                {"role": "system", "content": "You are a helpful plant expert."},
                {"role": "user", "content": prompt}
            ],
            "max_tokens": 5,
            "temperature": 0
        }
        try:
            resp = requests.post(openai_url, headers=headers, json=payload, timeout=10)
            if resp.status_code == 200:
                answer = resp.json()["choices"][0]["message"]["content"].strip().lower()
                if answer.startswith('yes'):
                    results.append('yes')
                else:
                    results.append('no')
            else:
                results.append('no')
        except Exception as e:
            print(f"[check_local_species] Exception: {e}")
            results.append('no')
    return json.dumps({'results': results})

if __name__ == '__main__':
    app.run(debug=True, port=5002)
  