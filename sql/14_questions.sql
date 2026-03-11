CREATE TABLE questions (
    id INT AUTO_INCREMENT PRIMARY KEY,
    test_id INT,
    question_text TEXT,

    option_a VARCHAR(255),
    option_b VARCHAR(255),
    option_c VARCHAR(255),
    option_d VARCHAR(255),

    correct_option CHAR(1),

    FOREIGN KEY (test_id) REFERENCES tests(id)
);