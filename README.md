# PeerPort 🌐

### *An Exclusive, Intra-Campus Peer-to-Peer Academic Resource Marketplace*

PeerPort is a dynamic full-stack web application designed exclusively for college campuses. It streamlines the student-to-student exchange of academic essentials like reference books, engineering tools (drafters, aprons, component kits), and study materials, creating a trusted, localized circular economy.

---

## 🚀 Key Features

* **Official College Email Authentication**: Restricts platform access exclusively to verified students using `@apsit.edu.in` institutional domains.
* **Dual-Phase Secure Registration**: Integrates mandatory 8-digit Moodle ID verification alongside phone tracking and simulated OTP confirmation via college email.
* **Strict Security & Access Policies**: Implements industrial-grade password hashing via `Flask-Bcrypt` with a robust validation policy (uppercase, lowercase, digits, special characters).
* **Vibrant User Experience**: Transitions away from monochrome dark elements into a high-fidelity dashboard customized with rich web graphics and academic filters.
* **User Privacy Protection**: Automatically processes academic profiles (Year, Semester, Department) for high-precision smart-matching while masking sensitive user contact data from public listings.

---

## 🛠️ Technical Stack

* **Frontend**: HTML5, CSS3 (Custom Layout Framework), JavaScript (ES6+), SVG Media.
* **Backend**: Python (Flask Framework) handles session management, structural validation, and server-side logic.
* **Database**: Relational SQLite architecture configured for localized execution (Production scalable to PostgreSQL).
* **Security**: Bcrypt cryptographic hashing, Regex domain validation, and secure Flask-Session routing.
* **Production Engine**: Gunicorn WSGI HTTP Server optimized for live hosting environments.

---

## ⚙️ Local Installation & Setup

Follow these steps to deploy PeerPort on your local machine:

1. **Clone the Repository**
   ```powershell
   git clone [https://github.com/aditipareekCodes/PeerPort_Project.git](https://github.com/aditipareekCodes/PeerPort_Project.git)
   cd PeerPort_Project