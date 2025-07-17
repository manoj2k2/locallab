# EDC Integration Platform - Architecture Design Document

**Version:** 1.0

**Date:** 2025-07-16

## 1. Introduction

### 1.1. Purpose

This document provides a comprehensive architecture and design for the Electronic Data Capture (EDC) Integration Platform. It is intended for software architects, developers, and project stakeholders to understand the system's structure, components, and technical approach.

### 1.2. System Overview

The EDC Integration Platform is a middleware system designed to reliably ingest data from a wide variety of sources within a lab environment. It validates, transforms, and enriches this data based on a configurable ruleset and routes the processed data to one or more target systems using their required protocols.

The core purpose is to decouple data producers from data consumers, creating a flexible, scalable, and maintainable data pipeline.

## 2. Architectural Drivers & Goals

The design is driven by the following key quality attributes:

*   **Flexibility & Extensibility:** The architecture must allow for the addition of new data sources and target systems with minimal changes to the core platform.
*   **Scalability:** The system must be able to handle high-volume data streams and sudden bursts of traffic without performance degradation or data loss.
*   **Reliability:** Data integrity is paramount. The system must guarantee message delivery and provide mechanisms for handling errors and component failures.
*   **Maintainability:** Components are designed to be independent and loosely coupled, allowing for easier development, testing, and maintenance.

## 3. System Context & Component Architecture

The following diagram illustrates the high-level architecture and the flow of data from source to target.

![High-Level Architecture Diagram](https://i.imgur.com/6V6K2V3.png)

### 3.1. Components and Responsibilities

#### 3.1.1. Input Adapters
*   **Responsibility:** To connect to external data sources and ingest data into the platform. Each adapter is a specialist for a specific protocol or data format.
*   **Implementation:** These are independent microservices or modules.
*   **Examples:**
    *   **REST API Adapter:** Exposes an HTTP endpoint for user forms or external software.
    *   **File Watcher Adapter:** Monitors a directory for incoming CSV files from systems like SAP.
    *   **MQTT Adapter:** Subscribes to an MQTT broker to receive real-time data from IoT devices.
    *   **Claim-Check Adapter:** For large payloads like MRI images, this adapter uploads the file to an object store and sends a lightweight metadata message (the "claim-check") to the hub.

#### 3.1.2. Data Ingestion Hub
*   **Responsibility:** To act as a central, persistent, and scalable buffer that decouples input adapters from the transformation engine.
*   **Implementation:** A message broker like RabbitMQ or Apache Kafka.
*   **Key Functions:**
    *   **Buffering:** Absorbs spikes in data volume, allowing the engine to process at a steady rate.
    *   **Routing:** Uses exchanges and queues (or topics) to route messages based on their type, content, or priority.
    *   **Durability:** Persists messages to disk to prevent data loss if the broker restarts.
    *   **Acknowledgement:** Ensures a message is not removed from the queue until it has been successfully processed.

#### 3.1.3. Transformation Engine
*   **Responsibility:** The core logic of the platform. It consumes standardized messages from the hub, applies business rules, and prepares the data for output.
*   **Implementation:** A scalable service (or group of services) that subscribes to the message hub.
*   **Key Functions (Config-Driven):**
    *   **Validation:** Checks data for completeness, correct types, and valid ranges.
    *   **Mapping:** Renames, restructures, and reformats data fields.
    *   **Enrichment:** Augments data by looking up additional information from external sources like databases.
    *   **Aggregation:** For stateful processing, it can collect and combine related messages before producing a final output.

#### 3.1.4. Output Adapters
*   **Responsibility:** To deliver the final, transformed data to the target systems, handling the specific protocol and security requirements for each.
*   **Implementation:** Independent microservices or modules that consume processed data.
*   **Examples:**
    *   **HTTP Output Adapter:** Sends data to a REST API, handling authentication and retry logic.
    *   **FTP/SFTP Output Adapter:** Formats data as a file (e.g., CSV, XML) and uploads it to an FTP server using atomic write patterns.
    *   **Database Output Adapter:** Connects to a SQL database and inserts records, often using performance-optimized batching.

## 4. Canonical Data Model

To ensure consistency within the platform, all data is wrapped in a standard message envelope as soon as it is ingested. This canonical model is what flows through the hub and engine.

**Example Canonical JSON Message:**
```json
{
  "metadata": {
    "messageId": "a7b1c9d2-e3f4-4a5b-8c6d-1e2f3a4b5c6d",
    "sourceSystem": "fever_device_iot",
    "sourceType": "temperature_reading",
    "sourceTimestamp": "2025-07-16T10:00:05Z",
    "ingestionTimestamp": "2025-07-16T10:00:06Z",
    "traceId": "trace-xyz-123"
  },
  "payload": {
    "device_id": "TEMP001",
    "temperature": 38.5,
    "unit": "Celsius"
  }
}
```

## 5. Technology Stack

| Component             | Technology                               |
| --------------------- | ---------------------------------------- |
| Programming Language  | Python 3.10+                             |
| Web Framework (APIs)  | FastAPI                                  |
| Data Ingestion Hub    | RabbitMQ (recommended for flexibility)   |
| Data Transformation   | Pandas, Custom Python Scripts            |
| Configuration         | YAML (`config.yml`)                      |
| Deployment            | Docker                                   |

## 6. Deployment View

The system is designed for containerization. Each adapter (input/output) and the transformation engine will be packaged as a separate Docker container. This allows for independent scaling and deployment.

*   A `docker-compose.yml` file will be used for local development and testing.
*   For production, a container orchestration platform like Kubernetes is recommended to manage scaling, health checks, and rolling updates.
