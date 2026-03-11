CREATE TABLE study_materials (
    id INT AUTO_INCREMENT PRIMARY KEY,
    title VARCHAR(255),
    file_name VARCHAR(255),
    subject_id INT,
    teacher_id INT,
    uploaded_at DATETIME DEFAULT CURRENT_TIMESTAMP,

    FOREIGN KEY (subject_id) REFERENCES subjects(id),
    FOREIGN KEY (teacher_id) REFERENCES users(id)
);