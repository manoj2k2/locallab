# Output Adapter - In-Depth Exploration

The role of the **Output Adapter** is to be a specialist in communication. It takes the fully processed and transformed data, which is in a standardized internal format, and handles the "last mile" of delivering it to a specific target system. This isolates the complexities of different communication protocols and authentication mechanisms from the core transformation logic.

Here are several common cases and how a dedicated Output Adapter solves them.

---

### Case 1: Delivering to a Modern REST API

*   **Problem:** The transformed patient data needs to be sent to a modern Electronic Health Record (EHR) system that exposes a secure `POST /api/v2/patient_records` endpoint. The request must include a JSON body and an `Authorization: Bearer <token>` header.
*   **Solution (HTTP Output Adapter):**
    *   This adapter is essentially an intelligent HTTP client.
    *   **Configuration:** It's configured with the target URL, the HTTP method (`POST`), and the necessary credentials (e.g., the Bearer Token or API Key). These secrets should be stored securely, not in the config file itself.
    *   **Execution:** When it receives the data object, it serializes it into a JSON string and constructs the HTTP request with the correct headers.
    *   **Error Handling:** If the API returns an error (e.g., `503 Service Unavailable`), the adapter shouldn't just drop the data. It should have a **retry policy** (e.g., retry up to 3 times with an exponential backoff delay). If the error is permanent (e.g., `400 Bad Request`), it should log the error and move the message to a "failed delivery" queue for investigation.

### Case 2: Dropping a File on an FTP/SFTP Server

*   **Problem:** A legacy analytics system doesn't have an API. It ingests data by polling a specific directory on a secure FTP server for new `.csv` files every hour.
*   **Solution (FTP/SFTP Output Adapter):**
    *   **Configuration:** This adapter is configured with the FTP server's hostname, port, username, password (or SSH key for SFTP), and the target directory path (`/incoming/lab_data/`).
    *   **Execution:**
        1.  It takes the transformed data object.
        2.  It formats the data into the required CSV format in memory.
        3.  It establishes a connection to the FTP server.
        4.  To prevent the target system from reading a partially written file, it first uploads the file with a temporary name (e.g., `data_part_xyz.tmp`).
        5.  Once the upload is complete, it issues a `RENAME` command to change the file to its final name (e.g., `lab_record_20250716_143015.csv`). This renaming operation is atomic on most file systems, ensuring the consumer only ever sees complete files.
    *   **Error Handling:** It handles connection timeouts, authentication failures, and disk space errors, with appropriate retry logic.

### Case 3: Writing Directly to a Database

*   **Problem:** The processed data needs to be stored directly in a SQL database table (e.g., a PostgreSQL or SQL Server database) for reporting purposes.
*   **Solution (Database Output Adapter):**
    *   **Configuration:** It holds the database connection string, which includes the server address, database name, and credentials. It also knows the target table name and the mapping from the data object's fields to the table's columns.
    *   **Execution:**
        1.  It receives the data object.
        2.  It establishes a connection to the database from a connection pool.
        3.  It constructs a parameterized SQL `INSERT` statement (e.g., `INSERT INTO lab_results (patient_id, test_name, value) VALUES (?, ?, ?)`). Using parameterized queries is critical to prevent SQL injection vulnerabilities.
        4.  It executes the statement within a transaction.
    *   **Batching for Performance:** If the data volume is high, a more advanced version of this adapter would not insert records one by one. It would collect a batch of records (e.g., 100 records or for 1 second) and perform a single, efficient bulk insert operation.

### Case 4: Forwarding to Another Enterprise System's Message Queue

*   **Problem:** The output of your system is the input for another downstream process within the enterprise, which uses its own separate message queue (e.g., a different RabbitMQ instance or an Azure Service Bus).
*   **Solution (AMQP/JMS Output Adapter):**
    *   This adapter is very similar to the Input Adapters but in reverse.
    *   **Configuration:** It's configured with the connection details for the *target* message broker and the name of the exchange or queue to publish to.
    *   **Execution:** It takes the processed data, ensures it's in the format expected by the downstream system, and publishes it as a new message to that external broker.
    *   **Benefit:** This further extends the decoupling pattern. Your system doesn't need to know anything about the downstream system's internal workings; it just needs to know how to hand off the message.

### Case 5: Sending to Multiple Destinations (Publish-Subscribe)

*   **Problem:** A single, transformed fever reading needs to be sent to the main hospital EHR (via API) *and* to a long-term archival storage system (via FTP).
*   **Solution (Routing Logic):**
    *   This isn't handled by a single adapter but by the handoff from the Transformation Engine.
    *   The configuration for the `fever_device` source would list multiple targets: `targets: ["hospital_ehr_api", "archive_ftp"]`.
    *   After transformation, the engine doesn't send the data directly to an adapter. Instead, it might publish it to an internal "fanout" exchange in the message broker.
    *   Separate queues for each output adapter (an `http_out_queue` and an `ftp_out_queue`) would be bound to this exchange. The message gets duplicated and sent to both queues.
    *   The HTTP Output Adapter listens to the `http_out_queue`, and the FTP Output Adapter listens to the `ftp_out_queue`, and they work independently and in parallel.
