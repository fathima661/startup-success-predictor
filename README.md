Startup Success Predictor

A full-stack web application built using Django that predicts the success probability of startups based on structured business and operational features. The system uses a trained machine learning model to generate predictions and provides users with insights into startup viability.

Project Overview

This project simulates a startup evaluation system where users can input business-related details such as funding stage, industry type, country, and other key attributes. The application processes this data using a machine learning model and returns a success probability score.

It also includes user authentication, dashboards, and an admin panel for managing users and evaluation records.

Features
User registration and login system
Session-based authentication
Startup evaluation form with structured inputs
Machine learning-based prediction system
Evaluation history tracking for each user
Admin dashboard for managing platform data
Responsive design for desktop and mobile
Interactive charts for result visualization
Clean dashboard interface for analytics
Tech Stack
Backend
Django (Python web framework)
Django authentication system
Django ORM
Machine Learning
Scikit-learn
Pandas
NumPy
Random Forest Classifier
Frontend
HTML
CSS
Bootstrap 5
JavaScript
Chart.js
Database
PostgreSQL (Neon cloud database)
Tools & Deployment
Python dotenv for environment variables
WhiteNoise for static file handling
Git and GitHub for version control
Machine Learning Model

The system uses a supervised learning approach.

Algorithm used: Random Forest Classifier

Input features include:

Funding stage
Industry type
Country
Market conditions
Operational attributes

Output:

A probability score indicating the likelihood of startup success
Modules
User authentication module
Startup evaluation module
Prediction engine
Dashboard and analytics module
Admin management module
Dashboard
Total evaluations per user
Average success score
Trend visualization using charts
Evaluation history table
Security
Environment variables used for sensitive information
Secure PostgreSQL connection with SSL
CSRF protection enabled
Session-based authentication system
Developer

Fathima Shaji