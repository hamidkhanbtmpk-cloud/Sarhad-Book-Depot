# 📚 Sarhad Book Depot - Full Management System

A comprehensive **Inventory Management, E-commerce, and Staff Payroll System** designed for local bookstores. This application streamlines stock tracking, online sales, automated billing, and employee performance.

## 🚀 Key Features

### 🛒 E-commerce & Sales
* **Online Ordering:** Customers can browse products, add to cart, and place orders with email confirmation.
* **Order Tracking:** Integrated tracking system for customers to check order status (Pending, Processing, Packed, Completed).
* **Smart Billing:** One-click invoice generation from online orders or manual billing with barcode support.

### 📦 Inventory Management
* **Stock Tracking:** Real-time monitoring of quantity, cost price, and sales price.
* **Category Management:** Organize products by category with low-stock alerts (less than 10 items).
* **Automated Calculations:** Auto-calculates total sales and net profit for the dashboard.

### 👥 Staff & Payroll Management
* **Attendance System:** Staff can "Clock In" and "Clock Out" with Admin approval workflow.
* **Payroll & Slips:** Automated salary reports with deductions for absences.
* **Role-Based Access:** Separate dashboards for Admin (full control) and Staff (task management).

### 📧 Communication & Security
* **Email Notifications:** Automated Order confirmations and Salary slips via Gmail SMTP.
* **Secure Login:** Password hashing using `pbkdf2:sha256` and OTP verification for signups/resets.

---

## 🛠️ Tech Stack
* **Backend:** Python (Flask)
* **Database:** SQLAlchemy (SQLite)
* **Frontend:** Responsive HTML5, CSS3, JavaScript (Dashboard charts using Chart.js)
* **Mailing:** Flask-Mail (SMTP Integration)

---

## ⚙️ Installation & Local Setup

1. **Clone the repository:**
   ```bash
   git clone [https://github.com/hamidkhanbtmpk-cloud/Sarhad-Book-Depot.git](https://github.com/hamidkhanbtmpk-cloud/Sarhad-Book-Depot.git)