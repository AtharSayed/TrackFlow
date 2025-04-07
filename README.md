# 🚦 Crowd Management System with QR Tracking

![Dashboard Screenshot](https://i.imgur.com/JQ8w5Ez.gif)  
*Real-time crowd analytics dashboard*

A Flask-based system for crowd monitoring using QR codes, with:
- **User registration** with family/friend networks  
- **QR-based identification**  
- **Lost person reporting**  
- **Real-time analytics dashboard**  
- **AI-powered risk prediction**

## 🌟 Key Features

| Feature | Description | Tech Used |
|---------|-------------|-----------|
| QR Generation | Unique QR for each user | `qrcode` `pyzbar` |
| Real-time Scanning | Webcam QR scanning | `OpenCV` `PyZbar` |
| Data Storage | Persistent user/report records | `MongoDB` |
| Live Dashboard | Registration heatmaps & analytics | `Streamlit` `Plotly` |
| Emergency Alerts | WebSocket notifications | `Flask-SocketIO` |

## 🛠 Setup Guide

### Prerequisites
- Python 3.8+
- MongoDB (local or Atlas)
- Webcam (for scanning)

### Installation
```bash
# Clone repository
git clone https://github.com/AtharSayed/TrackFlow.git
cd TrackFlow

# Install dependencies
pip install -r requirements.txt
