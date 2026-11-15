# SportsSync

**SportsSync** is a real-time, multi-sport tracking platform featuring an integrated AI Match Companion. Built with a robust microservice-inspired architecture, it ingests live telemetry and match data, piping it directly into a Retrieval-Augmented Generation (RAG) pipeline powered by the Google Gemini LLM.

Driven by a core vision to fundamentally **make sports better** and deeply engage fans, SportsSync transforms passive sports viewing into a highly interactive, data-driven second-screen experience.

## 🎯 Problem Statement & Solution

**The Problem: The In-Stadium Information Gap**

- While attending a match in person offers an unmatched atmosphere, fans in the stands face a significant information void. Cut off from live broadcast commentary, tactical overlays, and instant replays, in-stadium audiences often miss the nuances of the game. When a complex event occurs such as a confusing penalty decision, a sudden tactical substitution, or hidden telemetry changes like F1 sector times fans are left guessing about the technical "why" behind the live action. Static score apps fail to provide the deep, contextual analysis required by passionate fans and fantasy sports players.

**The Solution: A Personalized Analyst in Your Pocket**

- SportsSync bridges the gap between the raw stadium experience and broadcast-level analysis. By ingesting real-time telemetry (Formula 1) and live event timelines (Global Football) into a dynamic RAG pipeline, the platform empowers fans in the stands to simply *ask* an AI about the game in real-time. Whether an attendee needs to know "Why was that goal disallowed for Real Madrid?" or "What is the pace difference between the top two drivers?", SportsSync synthesizes live data into instant, conversational insights. This ensures that fans—whether optimising their fantasy lineups or just following their favourite team—enjoy a fully informed, immersive live sports experience.

## 👨‍🏫 Walkthrough 
<img width="1440" height="820" alt="Screenshot 2026-11-16 at 4 01 32 AM" src="https://github.com/user-attachments/assets/a45dab4c-0ec8-4d73-bfc0-8ec3d3868b8d" />

- **Register:** New users have to register using new `username` and `password`.

- **Login:** Already registered user can enter their registered credentials.

<img width="1440" height="819" alt="Screenshot 2026-11-16 at 4 02 31 AM" src="https://github.com/user-attachments/assets/65b9b396-2286-4ead-a39d-95695ce7b901" />

<img width="1440" height="819" alt="Screenshot 2026-11-16 at 4 02 51 AM" src="https://github.com/user-attachments/assets/1e8f3ed8-0af4-42f7-a551-e8c1e7b282c6" />

- If no live matches are scheduled cards will show stats of latest 2 played matches




## 🚀 Key Features

* **Multi-Sport RAG Companion:** Context-aware LLM chat rooms isolated by active sports sessions (F1 races vs. specific football fixtures).

* **Live Formula 1 Telemetry:** Real-time track status (flags), race leader tracking, and dynamic leaderboard standings via background asynchronous polling.

* **Global Football Ingestion:** Live and recent match tracking across La Liga, UCL, Premier League, and ISL.

* **Single Page Application (SPA):** Lightning-fast navigation with a custom hash-based router preserving UI states and browser history without page reloads.

* **Serverless NoSQL Persistence:** AWS DynamoDB integration for lightning-fast read/writes of user credentials and live chat histories.

* **JWT Authentication:** Secure user sessions with encrypted passwords and isolated chat rooms.

* **Dark Mode Support:** Fully responsive Tailwind CSS interface with dynamic, user-controlled theme toggling.

## 🛠️ Tech Stack

* **Frontend:** HTML5, Tailwind CSS, Vanilla JavaScript (Custom SPA Hash Router).

* **Backend:** Python 3.11, FastAPI, Uvicorn, Asyncio.

* **AI / LLM:** Google Gemini API.

* **Database:** AWS DynamoDB (via `boto3`).

* **External Data:** API-Football (v3), F1 Live Telemetry APIs.

* **Security:** JWT (JSON Web Tokens), bcrypt (Password Hashing), SlowAPI (Token Bucket Rate Limiting).

* **Infrastructure:** Docker, Docker Compose, AWS EC2.

## 🏗️ System Architecture & Design

SportsSync utilizes a monolithic application structure with internally decoupled services designed to operate concurrently without blocking the main event loop.

1. **The "Traffic Cop" RAG Router:**
   The `/ask` endpoint utilizes intelligent routing to handle multi-sport contexts. When a user submits a query, the backend inspects the `session_id`. If it begins with `football_`, it intercepts the request, calls the API-Football `/events` endpoint, formats a chronological timeline of goals/cards/subs, and injects it into the Gemini prompt. If it detects `f1_live`, it routes to the `state_manager` to pull live lap telemetry.

2. **DynamoDB Data Persistence:**
   The application leverages AWS DynamoDB as its primary NoSQL database to ensure low-latency data access at scale.

   * **Users Table:** Stores registered usernames and `bcrypt` hashed passwords.

   * **Chat History Table:** Contextually saves AI and user messages indexed by `username` and `session_id`. When a user switches between football matches or the F1 feed, their unique chat history for that specific event is instantly hydrated from DynamoDB.

3. **Background Ingestion Engine:**
   F1 telemetry is managed via FastAPI's `@asynccontextmanager` lifespan events. The `start_f1_ingestion` loop runs continuously in the background using `asyncio`, keeping the server's internal state fresh without relying on client-side requests to trigger updates.

4. **Client-Side Polling vs. Event-Driven Chat:**
   The UI utilizes a lightweight 4-second polling mechanism for live F1 leaderboards, while the AI chat interface operates on a strictly event-driven request/response cycle, conserving API quota and bandwidth.

## 🧠 Core Algorithms & Production Techniques

To elevate the application to production standards, several critical techniques and algorithms were implemented:

* **In-Memory TTL Caching (API Rate Limit Protection):**
  External sports APIs strictly limit request quotas (e.g., 100 requests/day). A custom Time-To-Live (TTL) dictionary cache was implemented in `football_ingestion.py`. If a league is queried within a 300-second (5-minute) window, the server returns the cached payload instantly. It prevents cache poisoning by refusing to cache empty fallback arrays (`[]`).

* **Heuristic API Fallbacks (Resiliency):**
  To handle API-Football's strict free-tier limits, the application features an automatic downgrade algorithm. It first attempts to fetch live matches (`live=all`). If empty, it falls back to fetching completed matches (`status=FT-AET-PEN`). To bypass paid parameter restrictions (`last=2` or date ranges), it defaults to querying the permitted `2024` free-tier season, chronologically sorts the payload via `lambda x: x["fixture"]["timestamp"]`, and slices the last two objects in Python.

* **Hash-Based SPA Routing:**
  Instead of using heavy frontend frameworks like React, the UI utilizes vanilla JavaScript listening to the `hashchange` window event (`#f1`, `#football-laliga`, `#match-12345`). This parses URL fragments to dynamically mount/unmount DOM nodes, preserving the native browser back-button behavior while maintaining a stateful WebSocket/Chat connection.

* **Token Bucket Rate Limiting:**
  To protect the Gemini LLM and database from spam, `SlowAPI` implements a token bucket algorithm on the `/ask` endpoint, limiting users to `5 requests / minute` mapped via their JWT token or IP address.

## 💻 Local Installation & Setup

1. **Clone the repository:**

   ```bash
   git clone https://github.com/riyo264/SportsSync.git
   cd SportsSync
   ```

2. **Environment Variables:**
   Create a `.env` file in the root directory and add your AWS, API, and JWT credentials:

   ```env
   FOOTBALL_API_KEY=your_api_football_key
   GEMINI_API_KEY=your_google_gemini_key
   SECRET_KEY=your_jwt_secret_string
   AWS_ACCESS_KEY_ID=your_aws_key
   AWS_SECRET_ACCESS_KEY=your_aws_secret
   AWS_DEFAULT_REGION=your_aws_region
   ```

3. **Run with Docker Compose:**

   ```bash
   docker compose up --build -d
   ```

   The application will be available at `http://localhost:8000`.

## ☁️ Deployment (AWS EC2)

The application is containerized and deployed to an AWS EC2 Ubuntu instance.

* **Port Mapping:** The `docker-compose.yml` binds container port `8000` to the host machine's port `80` (`0.0.0.0:80->8000/tcp`), allowing standard HTTP traffic over the public internet without port specification in the URL.

* **Process Management:** Uvicorn acts as the ASGI server managing the asynchronous FastAPI workers.

* **Manual Deployment:** Updates are deployed via SSH by pulling the latest code from the GitHub repository (`git pull origin main`) and executing a seamless detached Docker rebuild (`docker compose up --build -d`).
