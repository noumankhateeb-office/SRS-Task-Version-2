# Software Requirements Specification (SRS) for University Student Services Portal

---

### 1. Introduction

### 1.1 Purpose

This document provides the Software Requirements Specification (SRS) for a **University Student Services Portal**. The portal is intended to consolidate student-facing academic and administrative services including course registration, fee statements, timetable access, attendance review, advisor appointments, and document requests.

### 1.2 Scope

The solution will reduce manual service desk requests and provide a single web portal for students, faculty advisors, and academic administrators. The system will be built using **React**, **Python Django**, **PostgreSQL**, and **RESTful APIs**.

### 1.3 Definitions, Acronyms, and Abbreviations

- **Student**: A registered learner who uses the portal for academic and administrative services.
- **Advisor**: Faculty member responsible for reviewing academic progress and approving requests.
- **Registrar**: Administrative user managing enrollment rules and official records.
- **CGPA**: Cumulative Grade Point Average.

---

### 2. Overall Description

### 2.1 Product Perspective

The portal will sit alongside the university’s core academic records system and provide a modern self-service layer for common student workflows.

### 2.2 Product Features

- Student login and profile access
- Course registration and waitlist handling
- Fee statement and payment history review
- Attendance and grade visibility
- Advisor appointments and academic requests
- Digital document request tracking

### 2.3 User Classes and Characteristics

- **Student**: Uses self-service workflows for registration, records, and requests.
- **Advisor**: Reviews academic standing and approves advising-related requests.
- **Registrar**: Maintains schedules, enrollment rules, and official document workflows.

### 2.4 Operating Environment

- **Frontend**: Browser-based application for laptops and desktop devices.
- **Backend**: Django services with PostgreSQL and secured REST APIs.
- **Deployment**: Cloud environment with audit logging and monitoring.

### 2.5 Constraints

- Native mobile apps are out of scope for the first phase.
- Payment gateway integration will not be part of the initial release.
- Academic record edits must remain restricted to authorized administrative staff.

---

### 3. System Features and Requirements

### 3.1 Functional Requirements (FR)

**FR-01: Student Authentication**

- Students must be able to sign in using their university email and password.
- Password reset must be available through email verification.
- The system must log authentication failures and lock accounts after repeated invalid attempts.

**FR-02: Course Registration**

- Students must be able to browse available courses by semester, department, and instructor.
- The system must validate prerequisite completion, schedule conflicts, and seat availability before registration.
- When a course is full, eligible students should be able to join a waitlist.

**FR-03: Timetable and Attendance Review**

- Students must be able to view their weekly timetable after registration is complete.
- Attendance percentages must be displayed per course using the latest synced records.
- Faculty advisors must be able to review attendance trends for assigned students.

**FR-04: Fee Statement and Payment History**

- Students must be able to view current fee statements, due dates, and historical payments.
- The system must separate tuition, lab, hostel, and penalty charges in the statement view.
- Students should be able to download fee statements as PDF documents.

**FR-05: Advisor Appointment Requests**

- Students must be able to request appointments with their assigned advisor.
- Advisors must be able to approve, decline, or reschedule appointment requests.
- Appointment confirmations and changes must trigger notifications to both parties.

**FR-06: Academic Document Requests**

- Students must be able to request official documents such as transcripts, enrollment letters, and degree verification letters.
- Registrar staff must be able to update the request status through review, preparation, and completion stages.
- The system must record when documents are delivered digitally or collected in person.

**FR-07: Student Dashboard**

- The portal must provide a dashboard summarizing timetable, attendance alerts, pending requests, fee dues, and advisor notifications.
- Dashboard widgets should link users directly to the relevant service pages.

---

### 4. External Interface Requirements

### 4.1 User Interface

- The portal must meet WCAG 2.1 accessibility standards for core student workflows.

### 4.2 Software Interfaces

- The portal must consume data from the university’s existing student information system through secure APIs or scheduled synchronization.
- Email services must be used for password resets and appointment notifications.

---

### 5. System Attributes

### 5.1 Security

- Student records must only be visible to the authenticated student and authorized staff.
- Sensitive student data must be encrypted in transit and at rest.

### 5.2 Reliability

- Course registration and request tracking must maintain complete audit history for dispute resolution.

---

### 6. Out of Scope

- Online course delivery and virtual classroom features.
- Alumni services and admission application management.
