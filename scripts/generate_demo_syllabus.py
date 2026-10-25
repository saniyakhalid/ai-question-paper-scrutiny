import os

DEMO_SYLLABUS_TEXT = """AUTONOMOUS ENGINEERING COLLEGE - CURRICULUM SYLLABUS
DEPARTMENT OF COMPUTER SCIENCE & ENGINEERING
SUBJECT CODE: CS301
SUBJECT NAME: Machine Learning & Intelligent Systems
ACADEMIC YEAR: 2025-2026 | SEMESTER: VI

COURSE OUTCOMES (COs):
CO1: Understand the foundational concepts of supervised, unsupervised, and reinforcement learning.
CO2: Formulate and implement regression and classification algorithms for engineering datasets.
CO3: Design and evaluate tree-based ensemble models and kernel methods including SVM.
CO4: Analyze neural network architectures, deep learning fundamentals, and backpropagation.
CO5: Apply clustering, dimensionality reduction, and unsupervised techniques to complex domains.
CO6: Scrutinize ethical implications and deployment pipelines of intelligent AI systems.

SYLLABUS UNITS & TOPICS:

Unit 1: Introduction to Machine Learning & Statistical Foundations
- Machine Learning Paradigms: Supervised, Unsupervised, Reinforcement Learning
- Mathematical Preliminaries: Linear Algebra, Probability, Statistics
- Loss Functions, Cost Functions, Optimization Principles
- Gradient Descent, Stochastic Gradient Descent, Learning Rate Tuning

Unit 2: Linear Models & Regression Analysis
- Simple and Multiple Linear Regression
- Regularization: Ridge (L2), Lasso (L1), Elastic Net
- Logistic Regression for Binary and Multi-Class Classification
- Maximum Likelihood Estimation and Bias-Variance Tradeoff

Unit 3: Decision Trees, Ensemble Learning & Support Vector Machines
- Decision Tree Induction: ID3, C4.5, CART algorithms
- Splitting Criteria: Entropy, Information Gain, Gini Impurity
- Ensemble Methods: Bagging, Random Forests, Boosting (AdaBoost, Gradient Boost)
- Support Vector Machines: Linear Separation, Hyperplanes, Kernel Trick

Unit 4: Artificial Neural Networks & Deep Learning Basics
- Perceptron Model and Multi-Layer Perceptrons (MLP)
- Activation Functions: Sigmoid, Tanh, ReLU, Softmax
- Backpropagation Algorithm and Weight Optimization
- Introduction to Convolutional Neural Networks (CNN) and Recurrent Neural Networks (RNN)

Unit 5: Unsupervised Learning & Dimensionality Reduction
- Clustering Algorithms: K-Means, Hierarchical Clustering, DBSCAN
- Cluster Validation Metrics: Silhouette Coefficient, Elbow Criterion
- Dimensionality Reduction: Principal Component Analysis (PCA)
- Singular Value Decomposition (SVD) and Feature Selection Techniques

Unit 6: Model Evaluation, Validation & AI Ethics
- Cross-Validation Strategies: K-Fold, Stratified, Leave-One-Out
- Evaluation Metrics: Precision, Recall, F1-Score, ROC-AUC Curves
- Hyperparameter Tuning with Grid Search and Random Search
- Explainable AI, Fairness, Transparency, and Ethical AI Systems
"""

def generate():
    out_dir = os.path.join(os.path.dirname(os.path.dirname(__file__)), "uploads", "demo")
    os.makedirs(out_dir, exist_ok=True)
    out_file = os.path.join(out_dir, "CS301_Syllabus.txt")
    with open(out_file, "w", encoding="utf-8") as f:
        f.write(DEMO_SYLLABUS_TEXT)
    print(f"Generated demo syllabus at: {out_file}")

if __name__ == "__main__":
    generate()
