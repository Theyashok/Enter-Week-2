# 🌳 Tree Species Classifier (Flask App)

A modern, AI-powered web application for identifying **plant and tree species** from images of leaves, bark, or flowers. Built with Flask, PlantNet API, and OpenAI GPT, this tool is perfect for students, nature lovers, and botanists to explore the plant world interactively.

---

## 🚀 Features

- **AI-Powered Plant Identification:** Upload up to 5 images for more accurate results (leaves, bark, flowers, etc.).
- **Modern Web UI:** Glassmorphic, mobile-friendly interface with drag-and-drop, image preview, and reordering.
- **Confidence Scores:** Each result shows a high-confidence percentage.
- **Educational Content:** Fun facts and care tips for each species, generated by GPT.
- **Wikipedia-Style Summaries:** Short, readable summaries for each species.
- **Species Comparison:** Select two results to compare side-by-side in a stylish, GPT-generated HTML table.
- **Geographic Occurrence Map:** Shows where the species is found globally (via GBIF data).
- **Local Species Filter:** Use your location to filter results to those found within 100km.
- **Comments & Discussion:** Add and delete comments for each identified species.
- **Session Persistence:** Keeps results and comments in your browser session.
- **Error Handling:** Friendly error messages for API issues, timeouts, and image problems.

---

## 🌱 How It Works

1. 📤 **Upload** up to 5 clear images of a plant, tree, or leaf.
2. 🧠 The app processes the images using PlantNet and AI models.
3. 🌿 You receive a list of **likely species** with names, confidence, summaries, maps, and more.

---

## 💻 Tech Stack

- **Flask** (Python) – main backend and web server
- **HTML/CSS/JS** – custom frontend, with Tailwind CSS for styling
- **Pillow** – image processing
- **Requests** – API communication
- **PlantNet API** – plant species identification
- **OpenAI GPT-3.5** – summaries, education, and comparison
- **GBIF API** – species occurrence mapping

---

## 🧪 Getting Started

### 1. Clone the Repository

```bash
git clone <your-repo-url>
cd tree_classification_shell
```

### 2. Install Python Dependencies

```bash
pip install -r requirements.txt
```

### 3. Set Up API Keys

Create a file called `secrets.toml` in the project root with the following content:

```toml
[plantnet]
api_key = "your_plantnet_api_key"

[openai]
api_key = "your_openai_api_key"
```

You can get a PlantNet API key from [PlantNet](https://my.plantnet.org/).

### 4. Run the App

```bash
python app.py
```

The app will be available at [http://localhost:5002](http://localhost:5002).

---

## 📁 Project Structure

```
tree_classification_shell/
├── app.py
├── requirements.txt
├── secrets.toml
├── README.md
├── images/                # Temporary upload storage
├── static/
│   ├── tailwind.css       # Main CSS
│   └── tree.jpg           # Background image
├── tailwind.config.js     # (empty, for future styling)
├── package.json           # Frontend build dependencies (for Tailwind, not required to run)
└── Tree_Species_Classifier copy.ipynb # (Reference notebook, not required to run)
```

---

## 🧠 Ideal Use Cases

- 🌿 Botany & environmental science projects
- 🧪 Academic AI/ML demonstrations
- 🏕️ Nature education tools
- 🏫 Capstone project

---

## 🛡️ Disclaimer

This project is for **educational and research purposes** only. Results may vary depending on image quality, lighting, and angle.

---

## 👨‍💻 Author

**YASH GARG**

---

## 🌟 Give it a Star!

If you found this project helpful or interesting, don’t forget to ⭐ star the repository and share it with your friends!
