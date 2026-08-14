-- ==========================================
-- Dental Clinic Management System (DCMS)
-- Part 1 : Database & Master Tables
-- ==========================================
CREATE DATABASE IF NOT EXISTS dcms;
use dcms;

-- ==========================================
-- Patients Table
-- ==========================================

CREATE TABLE Patients (
    PatientID INT AUTO_INCREMENT PRIMARY KEY,
    FirstName VARCHAR(50),
    LastName VARCHAR(50),
    Gender VARCHAR(10),
    DOB DATE,
    Mobile VARCHAR(15),
    Email VARCHAR(100),
    Address TEXT,
    BloodGroup VARCHAR(5),
    Allergies TEXT,
    MedicalHistory TEXT,
    RegistrationDate DATE,
    Status VARCHAR(20)
);

-- ==========================================
-- Doctors Table
-- ==========================================

CREATE TABLE Doctors (
    DoctorID INT AUTO_INCREMENT PRIMARY KEY,
    DoctorName VARCHAR(100),
    Qualification VARCHAR(100),
    Specialization VARCHAR(100),
    Experience INT,
    Mobile VARCHAR(15),
    Email VARCHAR(100),
    AvailableDays VARCHAR(100),
    Status VARCHAR(20)
);

-- ==========================================
-- Staff Table
-- ==========================================

CREATE TABLE Staff (
    StaffID INT AUTO_INCREMENT PRIMARY KEY,
    Name VARCHAR(100),
    Role VARCHAR(50),
    Mobile VARCHAR(15),
    Email VARCHAR(100),
    JoiningDate DATE,
    Salary DECIMAL(10,2),
    Status VARCHAR(20)
);

-- ==========================================
-- Users Table
-- ==========================================

CREATE TABLE Users (
    UserID INT AUTO_INCREMENT PRIMARY KEY,
    Username VARCHAR(50),
    Password VARCHAR(255),
    Role VARCHAR(20),
    LastLogin DATETIME,
    Status VARCHAR(20)
);

-- ==========================================
-- Clinic Settings Table
-- ==========================================

CREATE TABLE ClinicSettings (
    SettingID INT AUTO_INCREMENT PRIMARY KEY,
    ClinicName VARCHAR(100),
    Address TEXT,
    Phone VARCHAR(20),
    Email VARCHAR(100),
    GSTNumber VARCHAR(30),
    WorkingHours VARCHAR(100)
);

CREATE TABLE Appointments (
    AppointmentID INT AUTO_INCREMENT PRIMARY KEY,
    PatientID INT,
    DoctorID INT,
    AppointmentDate DATE,
    AppointmentTime TIME,
    Purpose VARCHAR(200),
    Status VARCHAR(20),
    CreatedDate DATETIME,

    CONSTRAINT fk_appointment_patient
        FOREIGN KEY (PatientID)
        REFERENCES Patients(PatientID),

    CONSTRAINT fk_appointment_doctor
        FOREIGN KEY (DoctorID)
        REFERENCES Doctors(DoctorID)
);

CREATE TABLE Visits (
    VisitID INT AUTO_INCREMENT PRIMARY KEY,
    AppointmentID INT,
    VisitDate DATE,
    Symptoms TEXT,
    Diagnosis TEXT,
    DoctorNotes TEXT,
    NextVisitDate DATE,

    CONSTRAINT fk_visit_appointment
        FOREIGN KEY (AppointmentID)
        REFERENCES Appointments(AppointmentID)
);

-- ==========================================
-- Treatments Table
-- ==========================================

CREATE TABLE Treatments (
    TreatmentID INT AUTO_INCREMENT PRIMARY KEY,
    VisitID INT,
    DoctorID INT,
    TreatmentMasterID INT,
    Diagnosis TEXT,
    ProcedureName TEXT,
    ToothNo VARCHAR(10),
    Notes TEXT,
    BeforeImage VARCHAR(255),
    AfterImage VARCHAR(255),
    Status ENUM('Pending','Completed'),

    CONSTRAINT fk_treatment_visit
        FOREIGN KEY (VisitID)
        REFERENCES Visits(VisitID),

    CONSTRAINT fk_treatment_doctor
        FOREIGN KEY (DoctorID)
        REFERENCES Doctors(DoctorID),

    CONSTRAINT fk_treatment_master
        FOREIGN KEY (TreatmentMasterID)
        REFERENCES TreatmentMaster(TreatmentMasterID)
);

-- ==========================================
-- Prescriptions Table
-- ==========================================

CREATE TABLE Prescriptions (
    PrescriptionID INT AUTO_INCREMENT PRIMARY KEY,
    VisitID INT,
    DoctorID INT,
    Medicine VARCHAR(150),
    Dosage VARCHAR(100),
    Morning VARCHAR(50),
    Afternoon VARCHAR(50),
    Night VARCHAR(50),
    Days INT,
    Instruction TEXT,
    CreatedDate DATETIME,

    CONSTRAINT fk_prescription_visit
        FOREIGN KEY (VisitID)
        REFERENCES Visits(VisitID),

    CONSTRAINT fk_prescription_doctor
        FOREIGN KEY (DoctorID)
        REFERENCES Doctors(DoctorID)
);


CREATE TABLE Invoices (
    InvoiceID INT PRIMARY KEY AUTO_INCREMENT,
    VisitID INT NOT NULL,
    InvoiceNo VARCHAR(50) UNIQUE NOT NULL,
    InvoiceDate DATE NOT NULL,
    TotalAmount DECIMAL(10,2),
    Discount DECIMAL(10,2),
    Tax DECIMAL(10,2),
    NetAmount DECIMAL(10,2),
    Status ENUM('Pending','Paid','Cancelled') DEFAULT 'Pending',

    CONSTRAINT fk_invoice_visit
        FOREIGN KEY (VisitID)
        REFERENCES Visits(VisitID)
);

CREATE TABLE Payments (
    PaymentID INT PRIMARY KEY AUTO_INCREMENT,
    InvoiceID INT NOT NULL,
    PaymentDate DATETIME NOT NULL,
    Amount DECIMAL(10,2) NOT NULL,
    PaymentModeID VARCHAR(20),
    TransactionNo VARCHAR(100),
    Status ENUM('Pending','Completed','Failed') DEFAULT 'Completed',
    Remarks TEXT,

    CONSTRAINT fk_payment_invoice
        FOREIGN KEY (InvoiceID)
        REFERENCES Invoices(InvoiceID),
);

