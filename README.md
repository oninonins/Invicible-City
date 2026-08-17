# Invisible City

**AI-Powered Urban Accessibility Intelligence Platform**

*Push The Impact: Web Innovation for Sustainable Development Goals*

## 🎯 Target SDGs
* **Primary:** SDG 11 – Sustainable Cities and Communities
* **Supporting:** SDG 3 (Good Health and Well-being), SDG 4 (Quality Education), SDG 10 (Reduced Inequalities)

## 📖 Overview
Government agencies maintain datasets for public facilities such as schools, hospitals, bus stops, parks, and road networks. However, these datasets are often fragmented, making it difficult to evaluate whether public services are distributed fairly.

**Invisible City** is an AI-powered spatial analytics platform designed to help governments and urban planners measure public service accessibility, identify underserved areas, prioritize infrastructure development, and simulate the impact of future projects before implementation. 

Instead of just showing where facilities are located, the platform answers: 
> **"Which communities are underserved, and what infrastructure should be prioritized?"**

## ✨ Core Features
* **Interactive City Map**: View public facilities, population density, and risk zones on a single interactive map.
* **Urban Fairness Score (UFS)**: Calculate a public service equity score (0-100) for specific areas based on indicators like education, healthcare, and transport.
* **AI Recommendation Engine**: Generate infrastructure recommendations based on spatial analysis and UFS.
* **Priority Ranking**: Identify the top areas that require immediate infrastructure investment.
* **Analytics Dashboard**: City-level analytics on average UFS, accessibility trends, and facility distribution.

## 🛠️ Technology Stack
* **Frontend**: Next.js 15, TypeScript, Tailwind CSS, Leaflet/MapLibre
* **Backend**: FastAPI, Python, SQLAlchemy
* **Database**: PostgreSQL with PostGIS
* **AI & Spatial Engine**: GeoPandas, NetworkX, Pandas, Scikit-learn, OpenAI/Gemini API

## 🚀 Getting Started
This repository contains both the frontend and backend services.

1. Copy the example environment file:
   ```bash
   cp .env.example .env
   ```
2. Start the services using Docker Compose:
   ```bash
   docker compose up -d --build
   ```
3. Access the application:
   - **Frontend**: http://localhost:3000
   - **Backend API Docs**: http://localhost:8000/docs
