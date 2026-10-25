import os

DEMO_PAPER_TEXT = """AUTONOMOUS ENGINEERING COLLEGE
END-SEMESTER EXAMINATION - MAY 2026
BRANCH: B.TECH COMPUTER SCIENCE & ENGINEERING
SUBJECT: CS301 MACHINE LEARNING & INTELLIGENT SYSTEMS
TIME: 3 HOURS (180 MINUTES)                                              MAX MARKS: 100

-----------------------------------------------------------------------------------
Instructions to Candidates:
1. Answer all questions from SECTION A and any THREE from SECTION B.
2. Figures to the right indicate full marks.
3. Assume suitable data if necessary.
-----------------------------------------------------------------------------------

SECTION A

Q1(a) Define Machine Learning and explain the fundamental differences between Supervised, Unsupervised, and Reinforcement learning paradigms with real-world engineering examples. [10 Marks]

Q1(b) Describe the Gradient Descent algorithm for Linear Regression. Explain how learning rate affects convergence. [10 Marks]

Q2(a) Explain the Decision Tree algorithm. Define Entropy and Information Gain, and show how they are used for split selection. [10 Marks]
-- OR --
Q2(b) Explain the Random Forest ensemble classifier and describe how bagging reduces variance. [10 Marks]

SECTION B

Q3(a) Formulate the mathematical optimization problem for Support Vector Machines (SVM) for linear separation. [10 Marks]

Q3(b) Explain the Naive Bayes classification model based on Bayes Theorem. Mention its independence assumption. [10 Marks]

Q4(a) Derive the forward propagation and backpropagation error signal formulas for a feedforward artificial neural network. [10 Marks]

Q4(b) Compare CNN and RNN architectures with respect to spatial and temporal data applications. [10 Marks]

Q5(a) Explain the K-Means clustering algorithm step-by-step. Discuss how the value of K is chosen using the elbow method. [10 Marks]

Q5(b) Explain Principal Component Analysis (PCA) algorithm for dimensionality reduction. Detail covariance matrix computation. [10 Marks]
"""

def generate():
    out_dir = os.path.join(os.path.dirname(os.path.dirname(__file__)), "uploads", "demo")
    os.makedirs(out_dir, exist_ok=True)
    out_file = os.path.join(out_dir, "CS301_EndSem_2026.txt")
    with open(out_file, "w", encoding="utf-8") as f:
        f.write(DEMO_PAPER_TEXT)
    print(f"Generated demo paper at: {out_file}")

if __name__ == "__main__":
    generate()
