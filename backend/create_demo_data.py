#!/usr/bin/env python3
"""
Demo Data Creation Script for StudentsAI MVP
Populates a user account with realistic study data for demonstrations
"""

import os
import sys

sys.path.append(os.path.dirname(os.path.abspath(__file__)))

import uuid

from sqlalchemy.orm import Session

from app.config import DEBUG
from app.db.session import get_db
from app.models import Course
from app.repositories.flashcards import add_flashcard_tag, create_flashcard
from app.repositories.notes import create_note, set_note_tags
from app.repositories.users import get_user_by_email
from app.services.courses import create_course

DEMO_COURSE_NAME = "Demo course"


def create_demo_notes(db: Session, user_id: uuid.UUID, course_id: uuid.UUID):
    """Create realistic study notes with different topics"""

    notes_data = [
        {
            "title": "Machine Learning Fundamentals",
            "content": """
# Machine Learning Fundamentals

## What is Machine Learning?
Machine learning is a subset of artificial intelligence that enables computers to learn and improve from experience without being explicitly programmed.

## Types of Machine Learning
1. **Supervised Learning**: Learning from labeled data
2. **Unsupervised Learning**: Finding patterns in unlabeled data
3. **Reinforcement Learning**: Learning through interaction with environment

## Key Concepts
- **Training Data**: Data used to teach the model
- **Validation Data**: Data used to tune hyperparameters
- **Test Data**: Data used to evaluate final performance

## Popular Algorithms
- Linear Regression
- Decision Trees
- Random Forests
- Support Vector Machines
- Neural Networks

## Applications
- Image recognition
- Natural language processing
- Recommendation systems
- Fraud detection
            """,
            "tags": ["machine-learning", "ai", "data-science", "algorithms"],
        },
        {
            "title": "Quantum Physics Principles",
            "content": """
# Quantum Physics Principles

## Wave-Particle Duality
Light and matter exhibit both wave-like and particle-like properties depending on how they are observed.

## Heisenberg Uncertainty Principle
It is impossible to simultaneously know both the position and momentum of a particle with absolute precision.

## Quantum Superposition
A quantum system can exist in multiple states simultaneously until measured.

## Quantum Entanglement
Two or more particles can become correlated in such a way that the quantum state of each particle cannot be described independently.

## Schrödinger's Cat
A thought experiment illustrating quantum superposition and the measurement problem.

## Applications
- Quantum computing
- Quantum cryptography
- Quantum sensors
- Medical imaging
            """,
            "tags": ["physics", "quantum", "science", "theoretical"],
        },
        {
            "title": "Ancient Roman History",
            "content": """
# Ancient Roman History

## Founding of Rome
According to legend, Rome was founded in 753 BCE by Romulus and Remus.

## Roman Republic (509-27 BCE)
- Senate and popular assemblies
- Checks and balances system
- Expansion through military conquest
- Internal conflicts and civil wars

## Roman Empire (27 BCE-476 CE)
- Augustus as first emperor
- Pax Romana (Roman Peace)
- Extensive road network
- Advanced engineering and architecture

## Key Figures
- Julius Caesar
- Augustus
- Marcus Aurelius
- Constantine the Great

## Legacy
- Legal systems
- Architecture and engineering
- Language (Latin)
- Cultural influence
            """,
            "tags": ["history", "rome", "ancient", "civilization"],
        },
        {
            "title": "JavaScript ES6+ Features",
            "content": """
# JavaScript ES6+ Features

## Arrow Functions
```javascript
const add = (a, b) => a + b;
const multiply = (a, b) => {
    return a * b;
};
```

## Destructuring
```javascript
const { name, age } = person;
const [first, second] = array;
```

## Template Literals
```javascript
const greeting = `Hello, ${name}!`;
const multiline = `
    This is a
    multiline string
`;
```

## Spread Operator
```javascript
const newArray = [...oldArray, newItem];
const newObject = { ...oldObject, newProperty: value };
```

## Promises and Async/Await
```javascript
async function fetchData() {
    try {
        const response = await fetch(url);
        const data = await response.json();
        return data;
    } catch (error) {
        console.error('Error:', error);
    }
}
```

## Modules
```javascript
import { functionName } from './module.js';
export default class MyClass {};
```
            """,
            "tags": ["javascript", "programming", "es6", "web-development"],
        },
        {
            "title": "Nutrition and Health",
            "content": """
# Nutrition and Health

## Macronutrients
1. **Proteins**: Building blocks for muscles and tissues
2. **Carbohydrates**: Primary energy source
3. **Fats**: Essential for hormone production and cell membranes

## Micronutrients
- **Vitamins**: A, B, C, D, E, K
- **Minerals**: Iron, Calcium, Zinc, Magnesium

## Healthy Eating Principles
- Eat a variety of foods
- Include plenty of fruits and vegetables
- Choose whole grains over refined grains
- Limit added sugars and sodium
- Stay hydrated

## Meal Planning
- Breakfast: Protein + complex carbs
- Lunch: Balanced meal with protein
- Dinner: Lighter meal, avoid late eating
- Snacks: Nuts, fruits, yogurt

## Benefits of Good Nutrition
- Increased energy levels
- Better mental clarity
- Stronger immune system
- Healthy weight maintenance
- Reduced disease risk
            """,
            "tags": ["health", "nutrition", "wellness", "diet"],
        },
        # NEW INTERCONNECTED NOTES
        {
            "title": "Neural Networks Deep Dive",
            "content": """
# Neural Networks Deep Dive

## Building on ML Fundamentals
Neural networks are a subset of machine learning algorithms that mimic the human brain's structure.

## Architecture Components
- **Input Layer**: Receives data features
- **Hidden Layers**: Process information through weights and biases
- **Output Layer**: Produces predictions or classifications

## Activation Functions
- **ReLU**: Rectified Linear Unit, most common choice
- **Sigmoid**: Outputs values between 0 and 1
- **Tanh**: Outputs values between -1 and 1

## Training Process
1. **Forward Pass**: Data flows through the network
2. **Loss Calculation**: Compare prediction with actual value
3. **Backpropagation**: Update weights to minimize loss
4. **Gradient Descent**: Optimization algorithm

## Applications in Modern AI
- Computer vision (CNNs)
- Natural language processing (RNNs, Transformers)
- Speech recognition
- Game playing (AlphaGo, Dota 2)
            """,
            "tags": ["machine-learning", "neural-networks", "deep-learning", "ai"],
        },
        {
            "title": "Quantum Computing Applications",
            "content": """
# Quantum Computing Applications

## Connecting Quantum Physics to Computing
Quantum computing leverages quantum mechanical phenomena to process information in fundamentally new ways.

## Quantum Bits (Qubits)
Unlike classical bits that are 0 or 1, qubits can exist in superposition states, representing both values simultaneously.

## Quantum Algorithms
- **Shor's Algorithm**: Factor large numbers efficiently
- **Grover's Algorithm**: Search unsorted databases
- **Quantum Machine Learning**: Process data in quantum space

## Current State
- **IBM Q**: 433-qubit processors
- **Google Sycamore**: Achieved quantum supremacy
- **Microsoft**: Topological qubits approach

## Future Applications
- Drug discovery and molecular modeling
- Financial modeling and optimization
- Climate change simulation
- Cryptography and security
            """,
            "tags": ["quantum", "computing", "physics", "technology"],
        },
        {
            "title": "Roman Engineering and Architecture",
            "content": """
# Roman Engineering and Architecture

## Building on Roman History
The Romans were master builders whose innovations still influence modern construction.

## Architectural Innovations
- **Arches and Vaults**: Distributed weight efficiently
- **Concrete**: Revolutionary building material
- **Domes**: Pantheon's unreinforced concrete dome

## Engineering Marvels
- **Aqueducts**: Supplied cities with fresh water
- **Roads**: 50,000+ miles of paved highways
- **Bridges**: Stone arch bridges spanning rivers

## Construction Techniques
- **Opus Reticulatum**: Diamond-pattern stonework
- **Opus Incertum**: Irregular stone placement
- **Opus Testaceum**: Brick-faced concrete

## Legacy in Modern Times
- **Government Buildings**: Neoclassical architecture
- **Infrastructure**: Road and bridge design principles
- **Urban Planning**: Grid-based city layouts
            """,
            "tags": ["rome", "engineering", "architecture", "construction"],
        },
        {
            "title": "Modern Web Development",
            "content": """
# Modern Web Development

## Evolution from JavaScript ES6+
Building on ES6+ features, modern web development has evolved significantly.

## Frontend Frameworks
- **React**: Component-based UI library
- **Vue.js**: Progressive JavaScript framework
- **Angular**: Full-featured framework by Google

## Backend Technologies
- **Node.js**: JavaScript runtime for servers
- **Express.js**: Minimal web framework
- **Next.js**: React framework with SSR

## Modern Development Tools
- **TypeScript**: Typed JavaScript superset
- **Webpack/Vite**: Module bundlers
- **ESLint/Prettier**: Code quality tools

## Current Trends
- **JAMstack**: JavaScript, APIs, Markup
- **Progressive Web Apps**: Native app-like experience
- **WebAssembly**: High-performance web code
            """,
            "tags": ["javascript", "web-development", "frameworks", "modern"],
        },
        {
            "title": "Exercise and Fitness",
            "content": """
# Exercise and Fitness

## Complementing Nutrition and Health
Physical activity works synergistically with proper nutrition for optimal health.

## Types of Exercise
- **Cardiovascular**: Running, cycling, swimming
- **Strength Training**: Weightlifting, bodyweight exercises
- **Flexibility**: Yoga, stretching, pilates
- **Balance**: Tai chi, stability exercises

## Exercise Physiology
- **Aerobic System**: Uses oxygen for energy
- **Anaerobic System**: High-intensity, short duration
- **Muscle Hypertrophy**: Growth and adaptation

## Health Benefits
- **Cardiovascular Health**: Stronger heart and lungs
- **Mental Health**: Reduced stress and anxiety
- **Longevity**: Increased life expectancy
- **Disease Prevention**: Lower risk of chronic conditions

## Training Principles
- **Progressive Overload**: Gradually increase intensity
- **Specificity**: Train for your specific goals
- **Recovery**: Rest and adaptation periods
            """,
            "tags": ["health", "fitness", "exercise", "wellness"],
        },
        {
            "title": "Data Science Workflow",
            "content": """
# Data Science Workflow

## From ML Fundamentals to Practice
A systematic approach to solving problems with data and machine learning.

## Workflow Stages
1. **Problem Definition**: Clear objectives and success metrics
2. **Data Collection**: Gathering relevant datasets
3. **Data Cleaning**: Handling missing values and outliers
4. **Exploratory Analysis**: Understanding data patterns
5. **Feature Engineering**: Creating useful input variables
6. **Model Selection**: Choosing appropriate algorithms
7. **Training & Validation**: Building and testing models
8. **Deployment**: Putting models into production

## Tools and Technologies
- **Python**: pandas, numpy, scikit-learn
- **R**: Statistical computing and graphics
- **SQL**: Database querying and management
- **Visualization**: matplotlib, seaborn, plotly

## Real-World Applications
- **Business Intelligence**: Customer segmentation, churn prediction
- **Healthcare**: Disease diagnosis, drug discovery
- **Finance**: Risk assessment, fraud detection
- **Marketing**: Campaign optimization, personalization
            """,
            "tags": ["machine-learning", "data-science", "workflow", "analytics"],
        },
        {
            "title": "Classical Physics Foundations",
            "content": """
# Classical Physics Foundations

## Precursor to Quantum Physics
Understanding classical physics provides the foundation for quantum mechanics.

## Newton's Laws of Motion
1. **First Law**: Objects at rest stay at rest unless acted upon
2. **Second Law**: Force equals mass times acceleration
3. **Third Law**: For every action, there is an equal reaction

## Classical Mechanics
- **Kinematics**: Description of motion
- **Dynamics**: Forces causing motion
- **Energy**: Kinetic, potential, and conservation
- **Momentum**: Linear and angular momentum

## Wave Phenomena
- **Sound Waves**: Longitudinal pressure waves
- **Light Waves**: Electromagnetic radiation
- **Wave Properties**: Frequency, wavelength, amplitude

## Limitations
- **Macroscopic Scale**: Works well for everyday objects
- **High Speeds**: Breaks down near light speed
- **Small Scales**: Quantum effects become important
            """,
            "tags": ["physics", "classical", "mechanics", "waves"],
        },
        {
            "title": "Byzantine Empire",
            "content": """
# Byzantine Empire

## Continuation of Roman Legacy
The Byzantine Empire (330-1453 CE) was the Eastern continuation of the Roman Empire.

## Historical Timeline
- **Foundation**: Constantine moves capital to Constantinople
- **Golden Age**: Justinian's reign (527-565 CE)
- **Iconoclasm**: Religious image controversies
- **Decline**: Fall to Ottoman Turks in 1453

## Cultural Contributions
- **Orthodox Christianity**: Religious traditions and art
- **Greek Language**: Preserved classical knowledge
- **Architecture**: Hagia Sophia and other churches
- **Art**: Mosaics, icons, and illuminated manuscripts

## Political Structure
- **Emperor**: Absolute ruler with divine authority
- **Bureaucracy**: Complex administrative system
- **Military**: Professional army and navy
- **Diplomacy**: Strategic alliances and marriages

## Legacy
- **Eastern Europe**: Cultural and religious influence
- **Russia**: Adopted Orthodox Christianity
- **Renaissance**: Preserved classical texts for Europe
            """,
            "tags": ["history", "byzantine", "rome", "medieval"],
        },
        {
            "title": "Functional Programming",
            "content": """
# Functional Programming

## Modern JavaScript Paradigm
Building on ES6+ features, functional programming emphasizes pure functions and immutability.

## Core Concepts
- **Pure Functions**: No side effects, same input = same output
- **Immutability**: Data cannot be changed after creation
- **Higher-Order Functions**: Functions that take/return functions
- **Composition**: Combining functions to create new ones

## JavaScript Functional Features
```javascript
// Array methods
const numbers = [1, 2, 3, 4, 5];
const doubled = numbers.map(n => n * 2);
const evens = numbers.filter(n => n % 2 === 0);
const sum = numbers.reduce((acc, n) => acc + n, 0);

// Function composition
const compose = (...fns) => x => fns.reduceRight((y, f) => f(y), x);
const addOne = x => x + 1;
const multiplyByTwo = x => x * 2;
const addOneThenDouble = compose(multiplyByTwo, addOne);
```

## Benefits
- **Predictability**: Easier to test and debug
- **Parallelization**: Functions can run independently
- **Maintainability**: Clear data flow and transformations
            """,
            "tags": ["javascript", "programming", "functional", "es6"],
        },
        {
            "title": "Mental Health and Wellness",
            "content": """
# Mental Health and Wellness

## Holistic Health Approach
Mental health is as important as physical health and nutrition for overall wellness.

## Key Components
- **Emotional Regulation**: Understanding and managing feelings
- **Stress Management**: Coping with life's challenges
- **Social Connection**: Building meaningful relationships
- **Purpose and Meaning**: Finding direction in life

## Mental Health Practices
- **Mindfulness**: Present-moment awareness
- **Meditation**: Various techniques for mental clarity
- **Therapy**: Professional mental health support
- **Self-Care**: Activities that promote well-being

## Connection to Physical Health
- **Exercise**: Releases endorphins and reduces stress
- **Nutrition**: Brain health and mood regulation
- **Sleep**: Essential for mental recovery and processing
- **Social Activity**: Combats loneliness and depression

## Warning Signs
- Persistent sadness or anxiety
- Changes in sleep or appetite
- Withdrawal from activities
- Difficulty concentrating
            """,
            "tags": ["health", "mental-health", "wellness", "psychology"],
        },
    ]

    created_notes = []
    for note_data in notes_data:
        note = create_note(
            db=db,
            user_id=user_id,
            course_id=course_id,
            title=note_data["title"],
            content=note_data["content"],
        )
        set_note_tags(db, note, note_data["tags"])
        created_notes.append(note)
        print(f"Created note: {note.title}")

    return created_notes


def create_demo_flashcards(db: Session, user_id: uuid.UUID, notes):
    """Create flashcards from the notes"""

    flashcard_data = [
        # Machine Learning
        {
            "note_id": notes[0].id,
            "question": "What are the three main types of machine learning?",
            "answer": "Supervised Learning, Unsupervised Learning, and Reinforcement Learning",
            "tags": ["machine-learning", "types", "fundamentals"],
        },
        {
            "note_id": notes[0].id,
            "question": "What is the difference between training data and test data?",
            "answer": "Training data is used to teach the model, while test data is used to evaluate final performance",
            "tags": ["machine-learning", "data", "evaluation"],
        },
        {
            "note_id": notes[0].id,
            "question": "Name three popular machine learning algorithms",
            "answer": "Linear Regression, Decision Trees, Random Forests, Support Vector Machines, Neural Networks",
            "tags": ["machine-learning", "algorithms", "examples"],
        },
        # Quantum Physics
        {
            "note_id": notes[1].id,
            "question": "What is wave-particle duality?",
            "answer": "Light and matter exhibit both wave-like and particle-like properties depending on how they are observed",
            "tags": ["physics", "quantum", "duality"],
        },
        {
            "note_id": notes[1].id,
            "question": "What does the Heisenberg Uncertainty Principle state?",
            "answer": "It is impossible to simultaneously know both the position and momentum of a particle with absolute precision",
            "tags": ["physics", "quantum", "uncertainty"],
        },
        {
            "note_id": notes[1].id,
            "question": "What is quantum superposition?",
            "answer": "A quantum system can exist in multiple states simultaneously until measured",
            "tags": ["physics", "quantum", "superposition"],
        },
        # Roman History
        {
            "note_id": notes[2].id,
            "question": "When was Rome founded according to legend?",
            "answer": "753 BCE by Romulus and Remus",
            "tags": ["history", "rome", "founding"],
        },
        {
            "note_id": notes[2].id,
            "question": "What was the Pax Romana?",
            "answer": "The Roman Peace, a period of relative peace and stability during the Roman Empire",
            "tags": ["history", "rome", "peace"],
        },
        {
            "note_id": notes[2].id,
            "question": "Who was the first Roman emperor?",
            "answer": "Augustus (Octavian)",
            "tags": ["history", "rome", "emperors"],
        },
        # JavaScript
        {
            "note_id": notes[3].id,
            "question": "What are arrow functions in JavaScript?",
            "answer": "A concise way to write function expressions using the => syntax",
            "tags": ["javascript", "es6", "functions"],
        },
        {
            "note_id": notes[3].id,
            "question": "What is destructuring in JavaScript?",
            "answer": "A way to extract values from objects or arrays into distinct variables",
            "tags": ["javascript", "es6", "destructuring"],
        },
        {
            "note_id": notes[3].id,
            "question": "What does the spread operator (...) do?",
            "answer": "It expands iterables into individual elements, useful for copying arrays/objects",
            "tags": ["javascript", "es6", "spread"],
        },
        # Nutrition
        {
            "note_id": notes[4].id,
            "question": "What are the three macronutrients?",
            "answer": "Proteins, Carbohydrates, and Fats",
            "tags": ["nutrition", "macronutrients", "basics"],
        },
        {
            "note_id": notes[4].id,
            "question": "What are micronutrients?",
            "answer": "Vitamins and minerals that are needed in small amounts for proper body function",
            "tags": ["nutrition", "micronutrients", "vitamins"],
        },
        {
            "note_id": notes[4].id,
            "question": "What are the benefits of good nutrition?",
            "answer": "Increased energy, better mental clarity, stronger immune system, healthy weight, reduced disease risk",
            "tags": ["nutrition", "benefits", "health"],
        },
        # NEW INTERCONNECTED FLASHCARDS
        # Neural Networks (connects to ML Fundamentals)
        {
            "note_id": notes[5].id,
            "question": "What are the three main layers in a neural network?",
            "answer": "Input Layer, Hidden Layers, and Output Layer",
            "tags": ["neural-networks", "architecture", "deep-learning"],
        },
        {
            "note_id": notes[5].id,
            "question": "What is the most common activation function in modern neural networks?",
            "answer": "ReLU (Rectified Linear Unit)",
            "tags": ["neural-networks", "activation-functions", "modern-ai"],
        },
        {
            "note_id": notes[5].id,
            "question": "What is backpropagation in neural network training?",
            "answer": "A method to calculate gradients and update weights to minimize the loss function",
            "tags": ["neural-networks", "training", "optimization"],
        },
        # Quantum Computing (connects to Quantum Physics)
        {
            "note_id": notes[6].id,
            "question": "What is a qubit and how does it differ from a classical bit?",
            "answer": "A qubit can exist in superposition states representing both 0 and 1 simultaneously, unlike classical bits which are either 0 or 1",
            "tags": ["quantum", "computing", "qubits", "superposition"],
        },
        {
            "note_id": notes[6].id,
            "question": "What is quantum supremacy?",
            "answer": "When a quantum computer can solve a problem that classical computers cannot solve in a reasonable time",
            "tags": ["quantum", "computing", "supremacy", "breakthrough"],
        },
        {
            "note_id": notes[6].id,
            "question": "Name two quantum algorithms and their applications",
            "answer": "Shor's Algorithm for factoring large numbers efficiently, and Grover's Algorithm for searching unsorted databases",
            "tags": ["quantum", "algorithms", "applications"],
        },
        # Roman Engineering (connects to Roman History)
        {
            "note_id": notes[7].id,
            "question": "What was the revolutionary building material that the Romans developed?",
            "answer": "Concrete, which allowed them to build massive structures like the Pantheon dome",
            "tags": ["rome", "engineering", "concrete", "innovation"],
        },
        {
            "note_id": notes[7].id,
            "question": "How did Roman aqueducts work?",
            "answer": "They used gravity to transport fresh water from distant sources to cities through a system of channels and pipes",
            "tags": ["rome", "engineering", "aqueducts", "water-supply"],
        },
        {
            "note_id": notes[7].id,
            "question": "What architectural innovation allowed Romans to build large open spaces?",
            "answer": "Arches and vaults, which distributed weight efficiently and created strong, open structures",
            "tags": ["rome", "architecture", "arches", "vaults"],
        },
        # Modern Web Development (connects to JavaScript ES6+)
        {
            "note_id": notes[8].id,
            "question": "What is the main advantage of React's component-based architecture?",
            "answer": "Reusable, maintainable UI components that can be composed together to build complex interfaces",
            "tags": ["web-development", "react", "components", "architecture"],
        },
        {
            "note_id": notes[8].id,
            "question": "What is the difference between SSR and CSR in web development?",
            "answer": "SSR (Server-Side Rendering) generates HTML on the server, while CSR (Client-Side Rendering) generates it in the browser",
            "tags": ["web-development", "ssr", "csr", "rendering"],
        },
        {
            "note_id": notes[8].id,
            "question": "What is TypeScript and why is it useful?",
            "answer": "A typed superset of JavaScript that adds static type checking, making code more reliable and easier to maintain",
            "tags": ["web-development", "typescript", "javascript", "type-safety"],
        },
        # Exercise and Fitness (connects to Nutrition and Health)
        {
            "note_id": notes[9].id,
            "question": "What are the three energy systems used during exercise?",
            "answer": "ATP-PC system (immediate), Anaerobic glycolysis (short-term), and Aerobic system (long-term)",
            "tags": ["fitness", "exercise-physiology", "energy-systems"],
        },
        {
            "note_id": notes[9].id,
            "question": "What is progressive overload in strength training?",
            "answer": "Gradually increasing the intensity, volume, or difficulty of exercises to continue making progress",
            "tags": ["fitness", "strength-training", "progressive-overload"],
        },
        {
            "note_id": notes[9].id,
            "question": "How does exercise benefit mental health?",
            "answer": "Releases endorphins, reduces stress hormones, improves sleep, and provides social interaction opportunities",
            "tags": ["fitness", "mental-health", "wellness", "benefits"],
        },
        # Data Science Workflow (connects to ML Fundamentals)
        {
            "note_id": notes[10].id,
            "question": "What is the first step in the data science workflow?",
            "answer": "Problem Definition - clearly defining objectives and success metrics",
            "tags": ["data-science", "workflow", "problem-definition"],
        },
        {
            "note_id": notes[10].id,
            "question": "What is feature engineering in machine learning?",
            "answer": "Creating new input variables or transforming existing ones to improve model performance",
            "tags": ["data-science", "feature-engineering", "machine-learning"],
        },
        {
            "note_id": notes[10].id,
            "question": "Why is data cleaning important in data science?",
            "answer": "It ensures data quality by handling missing values, outliers, and inconsistencies that could affect model accuracy",
            "tags": ["data-science", "data-cleaning", "quality"],
        },
        # Classical Physics (connects to Quantum Physics)
        {
            "note_id": notes[11].id,
            "question": "What are Newton's three laws of motion?",
            "answer": "1) Objects at rest stay at rest unless acted upon, 2) Force equals mass times acceleration, 3) For every action there is an equal reaction",
            "tags": ["physics", "classical", "newton-laws", "mechanics"],
        },
        {
            "note_id": notes[11].id,
            "question": "What is the law of conservation of energy?",
            "answer": "Energy cannot be created or destroyed, only transformed from one form to another",
            "tags": ["physics", "classical", "conservation", "energy"],
        },
        {
            "note_id": notes[11].id,
            "question": "What are the main limitations of classical physics?",
            "answer": "It breaks down at very high speeds (relativity) and very small scales (quantum mechanics)",
            "tags": ["physics", "classical", "limitations", "modern-physics"],
        },
        # Byzantine Empire (connects to Roman History)
        {
            "note_id": notes[12].id,
            "question": "When did the Byzantine Empire begin and what event marked its start?",
            "answer": "330 CE when Constantine moved the capital from Rome to Constantinople (modern Istanbul)",
            "tags": ["byzantine", "history", "constantinople", "rome"],
        },
        {
            "note_id": notes[12].id,
            "question": "What was the Iconoclasm controversy in the Byzantine Empire?",
            "answer": "A religious dispute over whether religious images (icons) should be allowed in churches, lasting from 726-842 CE",
            "tags": ["byzantine", "history", "iconoclasm", "religion"],
        },
        {
            "note_id": notes[12].id,
            "question": "How did the Byzantine Empire preserve classical knowledge?",
            "answer": "By maintaining Greek as the official language and preserving ancient texts in monasteries and libraries",
            "tags": ["byzantine", "history", "classical-knowledge", "preservation"],
        },
        # Functional Programming (connects to JavaScript ES6+)
        {
            "note_id": notes[13].id,
            "question": "What is a pure function in functional programming?",
            "answer": "A function that has no side effects and always returns the same output for the same input",
            "tags": ["functional-programming", "pure-functions", "javascript"],
        },
        {
            "note_id": notes[13].id,
            "question": "What are higher-order functions?",
            "answer": "Functions that take other functions as arguments or return functions as results",
            "tags": ["functional-programming", "higher-order", "javascript"],
        },
        {
            "note_id": notes[13].id,
            "question": "What is function composition?",
            "answer": "Combining multiple functions to create a new function, where the output of one becomes the input of the next",
            "tags": ["functional-programming", "composition", "javascript"],
        },
        # Mental Health and Wellness (connects to Nutrition, Health, and Exercise)
        {
            "note_id": notes[14].id,
            "question": "How does exercise benefit mental health?",
            "answer": "Releases endorphins, reduces stress hormones, improves sleep, and provides social interaction opportunities",
            "tags": ["mental-health", "exercise", "wellness", "benefits"],
        },
        {
            "note_id": notes[14].id,
            "question": "What is mindfulness and how does it help mental health?",
            "answer": "Present-moment awareness that helps reduce stress, improve focus, and increase emotional regulation",
            "tags": ["mental-health", "mindfulness", "stress-reduction"],
        },
        {
            "note_id": notes[14].id,
            "question": "How do nutrition and mental health connect?",
            "answer": "Proper nutrition supports brain function, regulates mood, and provides energy for mental activities",
            "tags": ["mental-health", "nutrition", "brain-health", "wellness"],
        },
    ]

    created_flashcards = []
    for fc_data in flashcard_data:
        flashcard = create_flashcard(
            db=db,
            user_id=user_id,
            note_id=fc_data["note_id"],
            course_id=notes[0].course_id,
            question=fc_data["question"],
            answer=fc_data["answer"],
        )
        for tag in fc_data["tags"]:
            add_flashcard_tag(db, flashcard.id, user_id, tag)
        created_flashcards.append(flashcard)
        print(f"Created flashcard: {fc_data['question'][:50]}...")

    return created_flashcards


def main():
    """Main function to create demo data"""
    if DEBUG:
        print("🎯 Creating Demo Data for StudentsAI MVP...")

    # Get database session
    db = next(get_db())

    try:
        # Get user
        user = get_user_by_email(db, "supermens3000@gmail.com")
        if not user:
            if DEBUG:
                print("❌ User not found!")
            return

        if DEBUG:
            print(f"✅ Found user: {user.username} ({user.email})")

        # Replace an earlier demo course; deleting it cascades to its notes and flashcards
        previous = (
            db.query(Course)
            .filter(Course.user_id == user.id, Course.name == DEMO_COURSE_NAME)
            .all()
        )
        if previous:
            for course in previous:
                db.delete(course)
            db.commit()
            if DEBUG:
                print("✅ Removed the previous demo course")

        course = create_course(
            db, user.id, name=DEMO_COURSE_NAME, term=None, exam_date=None
        )

        # Create demo notes
        if DEBUG:
            print("\n📝 Creating demo notes...")
        notes = create_demo_notes(db, user.id, course.id)

        # Create demo flashcards
        if DEBUG:
            print("\n🃏 Creating demo flashcards...")
        flashcards = create_demo_flashcards(db, user.id, notes)

        if DEBUG:
            print("\n🎉 Demo data created successfully!")
            print(f"   📝 Notes: {len(notes)}")
            print(f"   🃏 Flashcards: {len(flashcards)}")
            print("\n🚀 Your account is now ready for screenshots and demos!")

    except Exception as e:
        if DEBUG:
            print(f"❌ Error creating demo data: {e}")
        db.rollback()
    finally:
        db.close()


if __name__ == "__main__":
    main()
