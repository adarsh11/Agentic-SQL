# 🎨 Agentic SQL Client - Premium UI

A modern, lucrative frontend for the Multi-Agent NLP-to-SQL system.

## ✨ Features
- **Modern Dashboard**: Clean, glassmorphic UI with a premium blue theme.
- **Deep Insights**: View agent reasoning, tool execution order, and evaluation feedback.
- **Query Suggestions**: One-click quick queries to get started.
- **Auto-Optimization**: Displays suggestions from the Evaluation Agent.
- **Code Highlighting**: Formatted PostgreSQL output for easy scanning.

## 🚀 Getting Started

### 1. Requirements
This is a standard Web application. You just need a way to serve static files.

### 2. Configuration
The frontend is pre-configured to point to `http://localhost:8000/generate-sql`. Ensure your backend is running on that port.

### 3. Running the App
You can use any local server. Here are a few common ways:

**Using Python (Recommended):**
```bash
# From the frontend folder
python -m http.server 3000
```
Then open `http://localhost:3000` in your browser.

**Using VS Code Live Server:**
Right-click `index.html` and select **"Open with Live Server"**.

**Using Node.js (serve):**
```bash
npx serve .
```

## 📂 File Structure
- `index.html`: Main structure and layouts.
- `style.css`: Premium blue design system and animations.
- `script.js`: API integration and dynamic UI logic.
