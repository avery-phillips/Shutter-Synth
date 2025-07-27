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

## Recent System Updates (July 2024)

### Enhanced Special Case Triggers & Mobile Optimization
- **Advanced Special Case Handling**: Implemented comprehensive triggers for specialized photography scenarios including astrophotography (skip lighting for no-gear scenarios), infrared photography (590nm/720nm with specific settings), drone photography (with FAA safety warnings), underwater photography, and group photography (depth of field guidance for f/4-f/5.6)
- **Enhanced Mobile Responsiveness**: Complete mobile-first redesign with touch-friendly 44px minimum button sizes, iOS-optimized input fields (16px font to prevent zoom), adaptive layouts for 768px and 480px breakpoints, and flexible button arrangements
- **Improved Beginner Flow Control**: Enhanced step-by-step progression with smart lighting step skipping, mobile flash recommendations, color temperature orange gel tips, and strict one-step-at-a-time delivery to prevent overwhelming beginners
- **Security & Rate Limiting**: Implemented IP-based rate limiting (5 requests per 60 seconds) on chat endpoints to prevent abuse and DoS attacks, with graceful error handling
- **Enhanced Knowledge Base**: Updated photography guidance with manual white balance recommendations (~4000-4500K for mixed lighting), RAW shooting emphasis, and flexible starting point language throughout all responses
- **Image Analysis Integration**: Full OpenAI GPT-4o vision integration supporting both inspiration analysis (how to recreate looks) and technique feedback (improve existing photos) with comprehensive lighting, composition, and gear-specific recommendations
- **Enhanced Context Management**: Implemented sophisticated conversational context tracking that maintains photography scenario state across follow-up questions, preventing context loss and providing relevant, targeted responses for posing, lighting, gear, and settings inquiries within established photography scenarios
- **Critical Bug Fixes**: Resolved duplicate response issue caused by improper conversation flow logic, fixed specialization validation mismatch, and added missing boudoir photography style to knowledge base for complete style coverage