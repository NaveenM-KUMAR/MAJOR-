# Community Parking System (CPS)
### *A Smart Collaborative Web Platform for Urban Parking Discovery, Private Space Monetization & Demand Optimization*

> **Final-Year Computer Science and Engineering Capstone Project (2026)**

---

## 1. Executive Summary & Problem Statement

Rapid urban vehicle growth combined with static parking infrastructure creates massive urban friction:
- **Search Inefficiencies**: Drivers spend an average of 15–20 minutes circulating downtown looking for open spots.
- **Environmental & Economic Drain**: Cruising for parking accounts for over 30% of downtown traffic congestion, millions of liters of wasted fuel, and significant carbon emissions ($CO_2$).
- **Safety Hazards**: Roadside illegal parking narrows arterial roads, encroaches onto pedestrian footpaths, and impedes emergency vehicles.
- **Underutilized Private Assets**: Simultaneously, thousands of residential driveways, commercial building bays, and community compounds remain empty during business and overnight hours.

**The Community Parking System (CPS)** bridges this gap by creating a secure, location-aware peer-to-peer sharing ecosystem. Property owners list idle driveway or garage capacity, while motorists discover, reserve, navigate to, and check into guaranteed parking spaces in real time.

---

## 2. Mandatory Technology Stack

| Component | Technology | Version / Specification |
| :--- | :--- | :--- |
| **Backend Framework** | Python / Flask | Flask 3.x with Modular Blueprints |
| **Database** | MySQL / SQLAlchemy ORM | Relational schema with Foreign Keys & Indexes |
| **Template Engine** | Jinja2 | Modular macros, custom filters, context processors |
| **Frontend Styling** | HTML5, CSS3, Bootstrap 5.3 | Responsive mobile-first grid, custom glassmorphic cards |
| **Interactive Maps** | Leaflet.js | OpenStreetMap tiles, custom marker pins, popups |
| **Data Visualizations**| Chart.js | Dynamic revenue lines, occupancy meters, donut charts |
| **Cryptographic Tokens**| Python `qrcode` + `Pillow` | Base64 dynamic QR generation & verification |
| **Testing Framework** | Pytest | Automated unit & concurrency test suite |

---

## 3. High-Level Architecture & Blueprint Structure

```
communityparkingsystem2nsdd/
├── app/
│   ├── __init__.py               # Flask application factory, database initialization, filters
│   ├── config.py                 # Intelligent DB connection detection (MySQL / SQLite fallback)
│   ├── models/                   # SQLAlchemy Relational Models
│   │   ├── user.py               # Driver, Owner, and Admin profiles & password hashing
│   │   ├── parking.py            # Parking spaces, specs, GPS coordinates, amenities, photos
│   │   ├── booking.py            # Booking lifecycle, time slots, prices, QR tokens, timestamps
│   │   ├── review.py             # 1–5 star ratings and driver feedback
│   │   ├── notification.py       # Role-based alerts & status updates
│   │   └── audit.py              # System activity logs for security & viva auditability
│   ├── routes/                   # Modular Flask Blueprints
│   │   ├── auth_routes.py        # Authentication, registration, profile settings
│   │   ├── driver_routes.py      # Search, details, booking, digital pass, emergency mode
│   │   ├── owner_routes.py       # Space CRUD, request approval, QR scanner, revenue charts
│   │   ├── admin_routes.py       # Owner verifications, user moderation, analytics, audit logs
│   │   └── api_routes.py         # Dynamic AJAX endpoints for availability, prediction, check-in
│   ├── services/                 # Decoupled Business Logic Services
│   │   ├── auth_service.py       # Registration validation, session security
│   │   ├── booking_service.py    # Authoritative concurrency & double-booking prevention engine
│   │   ├── prediction_service.py # Smart Availability Prediction statistical demand engine
│   │   ├── qr_service.py         # Dynamic Base64 QR code generator & token parser
│   │   ├── analytics_service.py  # Gross revenue metrics & system aggregation calculations
│   │   └── audit_service.py      # Traceable system event logging
│   ├── utils/                    # Reusable Utilities & Decorators
│   │   ├── decorators.py         # @login_required, @role_required, @approved_owner_required
│   │   ├── distance.py           # Haversine formula calculation & proximity ranking
│   │   └── file_handler.py       # Secure image validation & upload handler
│   ├── templates/                # Jinja2 Modular Presentation Layer
│   │   ├── base.html             # Master layout with responsive navbar & toast alerts
│   │   ├── index.html            # Landing page with hero search & feature showcases
│   │   ├── how_it_works.html     # Visual dual-role workflow guide
│   │   ├── auth/                 # login.html (with demo shortcuts), register.html, profile.html
│   │   ├── driver/               # dashboard, search, emergency, details, book, qr_ticket, my_bookings
│   │   ├── owner/                # dashboard, approval_status, manage_spaces, space_form, booking_requests, scanner, revenue
│   │   ├── admin/                # dashboard, owners_approval, spaces_manage, bookings_manage, users_manage, reviews_manage, analytics, audit_logs
│   │   └── errors/               # 400, 403, 404, 500 error pages
│   └── static/                   # Static Assets
│       ├── css/style.css         # Modern sleek UI styles, badges, animations
│       ├── js/main.js            # Dynamic availability AJAX helper, GPS detection
│       ├── js/maps.js            # Leaflet map pins, coordinates & popups
│       ├── js/charts.js          # Chart.js revenue & distribution renderers
│       └── uploads/              # Uploaded parking photos & verification docs
├── tests/                        # Comprehensive Test Suite (10/10 Passing)
│   ├── conftest.py               # In-memory test fixtures
│   ├── test_auth.py              # RBAC & authentication unit tests
│   ├── test_booking.py           # Double-booking & state transition concurrency tests
│   ├── test_qr.py                # QR generation, check-in & check-out validation
│   ├── test_prediction.py        # Smart prediction calculation tests
│   └── test_emergency.py         # Haversine distance & emergency prioritization tests
├── schema.sql                    # Production MySQL Relational Database Schema
├── seed_data.py                  # Realistic demo database populator
├── run.py                        # Server execution entry point
├── requirements.txt              # Complete dependency manifest
├── .env.example                  # Environment variable configuration template
└── README.md                     # Comprehensive documentation & Viva guide
```

---

## 4. Key Differentiating Features & Innovations

### A. Smart Availability Prediction Engine (`prediction_service.py`)
- **Explainable Statistical Engine**: Rather than opaque black boxes or simulated data, CPS computes demand scores by evaluating:
  1. **Current Active Occupancy Ratio**: Real-time slot count vs. active checked-in vehicles.
  2. **Rush Hour Peak Multiplier**: Morning (08:00–11:00) and evening (17:00–21:00) urban traffic volume curves.
  3. **Locality Cluster Booking Density**: 7-day trailing booking density across neighborhood parking spaces.
  4. **Historical Popularity**: Historical usage patterns for the specific driveway or lot.
- **Categorization Output**:
  - `LIKELY AVAILABLE`: High open slot probability, low historical congestion.
  - `OCCUPIED SOON`: Moderate capacity filling rapidly; pre-booking recommended.
  - `HIGH DEMAND AREA`: Locality cluster experiencing surge traffic.

### B. Emergency Parking Mode (`/driver/emergency`)
- Immediate, 1-click GPS-assisted parking locator designed for urgent scenarios (medical emergencies, vehicle overheating, urgent curbside clearance).
- Automatically filters only spaces with verified immediate availability, ranks strictly by Haversine distance, and provides 1-click Google Maps turn-by-turn routing with fast-track booking.

### C. Concurrency Engine & Anti-Double-Booking Protection (`booking_service.py`)
- Authoritative server-side transactional validation:
  $$\text{Overlap Condition: } (Start_{\text{existing}} < End_{\text{requested}}) \land (End_{\text{existing}} > Start_{\text{requested}})$$
- Ensures that count of overlapping active/approved bookings strictly $< Total\_Slots$.
- Protects against race conditions before database commit.

### D. QR Code Check-In & Check-Out Workflow (`qr_service.py`)
- Generates cryptographically secure, randomized booking tokens (`CPS-QR-xxxx`).
- Encodes token into dynamic high-resolution base64 PNG QR code tickets.
- Space owners scan or enter the token into the Check-In/Check-Out Terminal:
  - **Check-In**: Validates `APPROVED` status, transitions to `ACTIVE`, logs exact arrival timestamp.
  - **Check-Out**: Validates `ACTIVE` status, transitions to `COMPLETED`, auto-computes final fee, and updates the Owner Revenue Dashboard.

### E. Owner Revenue & Admin Analytics Dashboards
- **Owner Revenue Dashboard**: Real-time gross earnings, 7-day revenue trend line chart, average order value (AOV), occupancy utilization %, and per-space revenue breakdowns.
- **Admin Command Center**: System-wide KPIs, owner verification queue, high-demand locality tables, booking status distribution donut charts, review moderation, and full audit logs.

---

## 5. User Roles & Workflows

```mermaid
graph TD
    subgraph Driver Workflow
        D1[Register / Login] --> D2[Search with GPS / Locality]
        D2 --> D3[View Smart Prediction & Live Map]
        D3 --> D4[Select Time & Reserve Slot]
        D4 --> D5[Receive Digital QR Ticket Pass]
        D5 --> D6[Navigate via Maps & Present QR]
        D6 --> D7[Check-In -> Session ACTIVE]
        D7 --> D8[Check-Out -> Session COMPLETED]
        D8 --> D9[Submit 1-5 Star Review]
    end

    subgraph Owner Workflow
        O1[Register as Owner] --> O2[Pending Verification]
        O2 --> O3[Admin Approves Account]
        O3 --> O4[List Parking Spaces with Specs & GPS]
        O4 --> O5[Receive & Approve Booking Requests]
        O5 --> O6[Scan Driver QR at Arrival & Departure]
        O6 --> O7[View Real-Time Revenue Dashboard]
    end

    subgraph Admin Workflow
        A1[Admin Login] --> A2[Verify Pending Owner Applications]
        A2 --> A3[Moderate Spaces & User Accounts]
        A3 --> A4[Review High-Demand Area Heatmaps]
        A4 --> A5[Inspect Audit Log Trail]
    end
```

---

## 6. Installation & Execution Guide

### Prerequisites
- Python 3.10+ (Tested on Python 3.14)
- MySQL Server (Optional — system auto-detects and uses MySQL if reachable, or seamlessly falls back to SQLite for instant offline evaluation)

### Step 1: Clone or Navigate to Project
```bash
cd c:\Users\Shashwath\OneDrive\Desktop\communityparkingsystem2nsdd
```

### Step 2: Install Python Dependencies
```bash
pip install -r requirements.txt
```

### Step 3: Seed Demonstration Dataset
Populate the database with pre-configured users, parking spaces, historical revenue data, and reviews:
```bash
python seed_data.py
```

### Step 4: Run the Application
```bash
python run.py
```
Open your browser and navigate to: **`http://127.0.0.1:5000`**

---

## 7. Pre-Configured Demo Accounts (Viva Shortcuts)

The login screen includes **1-Click Auto-Fill Demo Buttons** for rapid viva demonstration:

| Role | Email Address | Password | Permissions & Portal |
| :--- | :--- | :--- | :--- |
| **System Admin** | `admin@cps.com` | `admin123` | Full admin console, owner approval, analytics, audit logs |
| **Parking Owner** | `owner1@cps.com` | `owner123` | Space management, request approvals, QR scanner, revenue |
| **Parking Owner** | `owner2@cps.com` | `owner123` | Active parking spaces in Indiranagar, revenue analytics |
| **Driver / User** | `driver1@cps.com` | `driver123` | Search, active booking ticket, QR pass, review history |
| **Driver / User** | `driver2@cps.com` | `driver123` | Upcoming bookings, search & booking access |

---

## 8. Automated Test Suite Execution

Run the complete test suite with verbose output:
```bash
pytest -v
```

### Test Coverage Breakdown
- `test_auth.py`: Driver registration, Owner pending state, duplicate protection, authentication & session security.
- `test_booking.py`: Anti-double-booking concurrency, slot capacity enforcement, overlapping time conflict checks, state lifecycle transitions (`PENDING -> APPROVED -> ACTIVE -> COMPLETED`).
- `test_qr.py`: Cryptographic QR generation, token validation, check-in timestamping, duplicate check-in prevention, check-out processing.
- `test_prediction.py`: Smart availability demand engine score and category evaluation.
- `test_emergency.py`: Haversine great-circle distance calculations and proximity sort.

**Result**: `10 passed in 6.46s (100% Passing)`

---

## 9. Viva Q&A & Academic Defense Guide

### Q1: How does your system prevent double booking of the same slot?
> **Answer**: We enforce authoritative server-side transactional validation in `booking_service.py`. Before any booking is created or approved, the engine executes an overlap query:
> `(Existing_Start < Requested_End) AND (Existing_End > Requested_Start)`.
> If the number of overlapping bookings with status in `['PENDING', 'APPROVED', 'ACTIVE']` meets or exceeds `parking_space.total_slots`, the request is rejected immediately.

### Q2: How does the Smart Availability Prediction feature work? Is it fake data?
> **Answer**: No, it is calculated directly from live database metrics in `prediction_service.py`. It uses an explainable weighted statistical model factoring in: (1) real-time active occupancy ratio, (2) hour-of-day rush curves (8–11 AM & 5–9 PM), (3) 7-day trailing booking density for that neighborhood cluster, and (4) historical space utilization. It returns `LIKELY AVAILABLE`, `OCCUPIED SOON`, or `HIGH DEMAND AREA` with human-understandable explanations.

### Q3: What is the purpose of the Owner Verification Workflow?
> **Answer**: Community parking requires high trust and safety. When a property owner registers, their account enters a `PENDING` state. They cannot make parking listings publicly bookable until an Administrator verifies their property address and identity documents from the Admin console.

### Q4: How is data privacy maintained in QR Code tickets?
> **Answer**: Personal identifying details (passwords, payment data, personal notes) are never encoded directly into the QR image. The QR payload contains only a randomized cryptographic token reference (`CPS-QR-xxxx`). When scanned, the backend resolves the token to the authorized booking record.
