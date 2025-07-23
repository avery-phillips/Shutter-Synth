# Shutter Synth - Photography Assistant Web Application

## Overview

Shutter Synth is a Flask-based web application featuring Synthia, an AI photography assistant that provides personalized shoot planning advice. The application adapts its response style based on user skill levels and their personal gear inventory, offering tailored guidance for various photography styles including portrait, fashion, sports, glamour, and boudoir photography.

## User Preferences

Preferred communication style: Simple, everyday language.

## System Architecture

### Backend Architecture
- **Framework**: Flask web application with SQLAlchemy ORM
- **Database**: SQLite with fallback support (configured to use DATABASE_URL environment variable)
- **Session Management**: Flask sessions with configurable secret key
- **Middleware**: ProxyFix for proper header handling in deployment environments

### Frontend Architecture
- **Template Engine**: Jinja2 templates with Bootstrap dark theme
- **CSS Framework**: Bootstrap with custom CSS for dark theme and chat interface
- **JavaScript**: Vanilla JavaScript for interactive chat functionality
- **Icons**: Font Awesome for consistent iconography

### Data Architecture
- **User Management**: Simple user system with username-based identification
- **Gear Management**: Flexible JSON-based storage for various equipment types
- **Chat System**: Session-based conversations with message history and context tracking

## Key Components

### Models (models.py)
- **User**: Stores user profile, skill level, and timestamps
- **GearItem**: Flexible gear storage with category, brand, model, and JSON specifications
- **ChatSession**: Manages conversation sessions with step tracking for beginners
- **ChatMessage**: Individual message storage (referenced but not fully implemented)

### Chat Engine (chat_engine.py)
- **SynthiaChatEngine**: Core AI logic that adapts responses based on skill level
- **Knowledge Base**: JSON-based photography expertise storage
- **Intent Classification**: Processes user input to determine photography style requests
- **Gear Matching**: Filters user's equipment for relevant recommendations

### Routes (routes.py)
- **Onboarding Flow**: User registration with skill level selection
- **Gear Management**: Equipment input and management interface
- **Chat Interface**: Real-time conversation with adaptive responses
- **Profile Management**: Skill level updates and user preferences

### Knowledge Base (photography_knowledge.json)
- **Comprehensive Responses**: Full setup information for intermediate/advanced users
- **Step-by-Step Guides**: 4-step breakdown for beginner users
- **Multiple Photography Styles**: High-key portraits, dark moody fashion, and more
- **Keyword Matching**: Intent classification based on user input

## Data Flow

### User Onboarding
1. User selects username and skill level
2. System creates User record and stores session data
3. User inputs gear information through guided forms
4. GearItem records are created and linked to user

### Chat Interaction
1. User submits photography request in natural language
2. SynthiaChatEngine classifies intent and extracts photography style
3. System matches user's gear to style requirements
4. Response is generated based on skill level:
   - **Beginner**: Step-by-step guidance with continuation prompts
   - **Intermediate/Advanced**: Comprehensive single response
5. ChatSession tracks conversation state and step progress

### Adaptive Response Logic
- **Beginner Mode**: 4-step process (Scene & Gear → Lighting → Posing & Composition → Pro Tips)
- **Continuation Handling**: Waits for user confirmation between steps
- **Decline Handling**: Graceful exit when user doesn't want to continue
- **Context Preservation**: Maintains conversation state across interactions

## External Dependencies

### Python Packages
- **Flask**: Web framework and routing
- **SQLAlchemy**: Database ORM and migrations
- **Werkzeug**: WSGI utilities and middleware

### Frontend Libraries
- **Bootstrap 5**: UI framework with dark theme support
- **Font Awesome**: Icon library for consistent visual elements
- **Custom CSS**: Chat interface styling and animations

### Data Sources
- **photography_knowledge.json**: Static knowledge base for photography expertise
- **SQLite Database**: User data, gear inventory, and chat history

## Deployment Strategy

### Development Configuration
- **Debug Mode**: Enabled for development with hot reload
- **Database**: SQLite file-based storage with automatic table creation
- **Session Security**: Configurable secret key with fallback for development

### Production Considerations
- **Database URL**: Environment variable support for external databases
- **Connection Pooling**: Configured with pool_recycle and pre_ping for reliability
- **Proxy Support**: ProxyFix middleware for proper header handling behind reverse proxies
- **Logging**: Configurable logging levels for debugging and monitoring

### Scalability Features
- **Stateless Design**: Session-based user management allows for horizontal scaling
- **Flexible Gear Storage**: JSON specifications support diverse equipment types
- **Modular Chat Engine**: Separate business logic allows for easy AI model integration
- **Template Inheritance**: Consistent UI framework for easy maintenance and updates

The application is designed to be easily deployable on platforms like Replit, Heroku, or similar cloud services, with minimal configuration required for basic functionality while supporting more robust database solutions for production use.