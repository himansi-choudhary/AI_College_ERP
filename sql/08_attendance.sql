CREATE TABLE attendance (
    id INT AUTO_INCREMENT PRIMARY KEY,
    student_id INT NOT NULL,
    subject_id INT NOT NULL,
    date DATE NOT NULL,
    status ENUM('Present','Absent') NOT NULL,
    UNIQUE(student_id, subject_id, date),
    FOREIGN KEY (student_id) REFERENCES users(id),
    FOREIGN KEY (subject_id) REFERENCES subjects(id)
);