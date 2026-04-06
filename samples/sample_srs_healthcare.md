# Software Requirements Specification (SRS) for Healthcare Patient Portal

---

### 1. Introduction

### 1.1 Purpose

This document describes the Software Requirements Specification (SRS) for a Healthcare Patient Portal, a web-based application that allows patients to manage appointments, view medical records, and communicate with healthcare providers.

### 1.2 Scope

The Patient Portal will provide appointment scheduling, medical record access, prescription management, secure messaging with doctors, and billing features. The platform is built using **Angular**, **Spring Boot**, and **PostgreSQL**.

### 1.3 Definitions, Acronyms, and Abbreviations

- **Patient**: A registered user who uses the portal to access healthcare services.
- **Doctor**: A healthcare provider who manages patient appointments and records.
- **Admin**: System administrator who manages users and system settings.
- **System**: The Healthcare Patient Portal being developed.
- **EHR**: Electronic Health Record.

---

### 2. Overall Description

### 2.1 Product Perspective

The Healthcare Patient Portal is a standalone web application that serves as a bridge between patients and healthcare providers, enabling digital access to healthcare services.

### 2.2 Product Features

- **Appointment Scheduling**: Patients can book, reschedule, and cancel appointments.
- **Medical Records**: Patients can view their medical history, lab results, and prescriptions.
- **Secure Messaging**: HIPAA-compliant messaging between patients and doctors.
- **Billing and Payments**: View invoices and make payments online.
- **Prescription Management**: View current prescriptions and request refills.

### 2.3 User Classes and Characteristics

- **Patient**: Primary users who access their health information and schedule appointments.
- **Doctor**: Healthcare providers who manage patient care through the portal.
- **Admin**: System administrators responsible for user management and configuration.

### 2.4 Operating Environment

- **Frontend**: Angular SPA compatible with Chrome, Firefox, Safari, and Edge.
- **Backend**: Java Spring Boot REST API with PostgreSQL database.

### 2.5 Constraints

- All data handling must comply with HIPAA regulations.
- The system must integrate with existing hospital EHR systems via HL7 FHIR API.
- No telemedicine or video consultation features are included.

---

### 3. System Features and Requirements

### 3.1 Functional Requirements

### FR-01: Appointment Booking

- **Requirements**:
    - Patients can view available time slots for each doctor.
    - Patients can book appointments by selecting a doctor, date, and time.
    - System sends confirmation email and SMS after booking.
    - Patients can cancel or reschedule at least 24 hours before appointment.
- **Acceptance Criteria**:
    - Available slots display correctly for selected doctor and date.
    - Booking creates appointment record and blocks the time slot.
    - Confirmation notifications are sent within 1 minute.
    - Cancellation within 24 hours is prevented with appropriate message.

### FR-02: Medical Records Access

- **Requirements**:
    - Patients can view their complete medical history.
    - Records include diagnoses, treatments, lab results, and imaging reports.
    - Records are displayed in reverse chronological order.
    - Patients can download records as PDF.
- **Acceptance Criteria**:
    - All patient records load correctly in chronological order.
    - Lab results display with normal range indicators.
    - PDF download contains complete and formatted record.
    - Access to records is logged for audit purposes.

### FR-03: Secure Messaging

- **Requirements**:
    - Patients can send messages to their assigned doctors.
    - Messages support text and file attachments (up to 5MB).
    - All messages are encrypted in transit and at rest.
    - Doctors can reply from their dashboard.
- **Acceptance Criteria**:
    - Messages are delivered to the recipient's inbox.
    - File attachments upload and download correctly.
    - Messages are encrypted using AES-256 encryption.
    - Both parties receive notification for new messages.

### FR-04: Prescription Refill Request

- **Requirements**:
    - Patients can view current active prescriptions.
    - Patients can request refills for eligible prescriptions.
    - Doctor receives refill request notification for approval.
    - System tracks refill history.
- **Acceptance Criteria**:
    - Active prescriptions display with medication name, dosage, and refill count.
    - Refill request is submitted and doctor is notified.
    - Approved refill updates prescription record.
    - Refill history shows all past requests with status.

---

### 3.2 Non-Functional Requirements

### NFR-01: Security and Compliance

- **Requirements**:
    - System must comply with HIPAA privacy and security rules.
    - All PHI (Protected Health Information) must be encrypted at rest and in transit.
    - Multi-factor authentication required for all users.
    - Audit logging for all data access and modifications.

### NFR-02: Performance

- **Requirements**:
    - Page load time under 3 seconds.
    - System shall support 2000 concurrent users.
    - Database queries shall complete under 1 second.

### NFR-03: Availability

- **Requirements**:
    - System uptime of 99.95%.
    - Automated failover for critical services.
    - Disaster recovery plan with RPO of 1 hour and RTO of 4 hours.

---

### 4. External Interface Requirements

### 4.1 User Interface

- Accessible web interface following WCAG 2.1 AA standards.
- Support for screen readers and keyboard navigation.

### 4.2 Software Interfaces

- Integration with hospital EHR via HL7 FHIR API.
- Integration with payment gateway for online billing.
- Integration with SMS gateway for appointment reminders.

---

### 5. System Attributes

### 5.1 Reliability

- System must be available 99.95% of the time with automated failover.

### 5.2 Scalability

- Microservices architecture to allow independent scaling of appointment, messaging, and records services.

### 5.3 Security

- HIPAA-compliant data encryption, access controls, and audit logging. Multi-factor authentication for all users.

### 5.4 Maintainability

- Microservices architecture with CI/CD pipeline. Comprehensive logging and monitoring.

---

### 6. Out of Scope

- Telemedicine and video consultations.
- Insurance claim processing.
- Pharmacy integration for automated prescription fulfillment.
- Mobile native applications.
