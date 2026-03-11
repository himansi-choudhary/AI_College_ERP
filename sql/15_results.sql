CREATE TABLE results (
    id INT AUTO_INCREMENT PRIMARY KEY,
    student_id INT,
    test_id INT,
    score INT,
    submitted_at DATETIME DEFAULT CURRENT_TIMESTAMP,

    FOREIGN KEY (student_id) REFERENCES users(id),
    FOREIGN KEY (test_id) REFERENCES tests(id)
);