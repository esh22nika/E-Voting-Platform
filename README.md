# 🗳️ Online E-Voting Platform

_A secure, cloud-based voting system for accessible and tamper-proof elections_

![Demo Screenshot](media/demo.gif) _(Optional: Add a GIF later)_

## 📌 Overview

A Django-based e-voting platform enabling:

- **Secure OTP-based voter authentication** (email/SMS).
- **Real-time election monitoring** (WebSockets + Redis).
- **Admin-managed elections** (candidates, voting windows).
- **Accessibility-focused UI** (screen reader support, high-contrast mode).

**Target Users**: Remote voters, elderly, PWDs.  
**Inspired By**: Bihar's e-voting pilot + NATO election security standards.

---

## 🛠️ Tech Stack

| Component         | Technology Used                            |
| ----------------- | ------------------------------------------ |
| Frontend          | HTML, CSS, JS, Bootstrap                   |
| Backend           | Django + Django REST Framework             |
| Database          | SQLite (Dev) → **Azure PostgreSQL** (Prod) |
| Real-Time Updates | Django Channels + Redis                    |
| Async Tasks       | Celery + RabbitMQ                          |
| Security          | OTP, encrypted receipts, MAC binding       |
| Deployment        | Docker, Azure App Service                  |

---

## 🌟 Key Features

### **1. Voter Flow**

- 📱 OTP login (email/SMS).
- ✅ Vote once per election (MAC address binding).
- 📧 Encrypted vote receipts.

### **2. Admin Flow**

- ⚙️ Create/manage elections (start/end times, candidates).
- 📊 Live dashboards (WebSocket-powered results).

### **3. Security**

- 🔒 2 voters max per mobile number.
- ⏳ Time-bound voting windows.

---

## 🚀 Setup Guide

### **Prerequisites**

- Python 3.9+, Docker, Azure account (for cloud deployment).

### **Local Development**

1. Clone the repo:
   ```bash
   git clone https://github.com/esh22nika/E-Voting-Platform.git
   cd E-Voting-Platform
   ```

## ✅ **Completed Features**

| Feature                | Progress | Notes                              |
| ---------------------- | -------- | ---------------------------------- |
| **Voter Registration** | ✔️ 70 %  | OTP via email, voter ID validation |
| **Election Creation**  | ✔️ 100%  | Admin can set candidates/times     |
| **Basic Voting Flow**  | ✔️ 100%  | Vote casting + SQLite persistence  |
| **Admin Dashboard**    | ✔️ 80%   | Real-time results (WebSockets WIP) |
| **Docker Setup**       | ✔️ 100%  | Containerized backend              |

---

## 🚧 **To-Do Features**

| Feature                 | Priority  | Notes                              |
| ----------------------- | --------- | ---------------------------------- |
| **Face Verification**   | 🔴 High   | AWS Rekognition integration        |
| **voter registration**  |
| **MAC Address Binding** | 🟠 Medium | Limit 2 voters per device          |
| **Azure PostgreSQL**    | 🟢 Low    | Migrate from SQLite for production |
| **Blockchain Auditing** | 🔴 High   | Immutable vote logs                |
| **Multi-Language UI**   | 🟢 Low    | Accessibility expansion            |

---

## 🛠️ **In Progress**

- **Real-Time Updates**: WebSocket integration (80% done).
- **Encrypted Receipts**: Cryptographic hashing (testing phase).
