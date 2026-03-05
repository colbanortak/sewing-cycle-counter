from setuptools import setup, find_packages

setup(
    name="sewing-cycle-counter",
    version="0.1.0",
    description="AI-powered sewing cycle counter for workshop performance tracking",
    author="ÇOLBAN Elektrik Otomasyon",
    packages=find_packages(),
    python_requires=">=3.10",
    install_requires=[
        "mediapipe>=0.10.9",
        "opencv-python>=4.9.0",
        "numpy>=1.24.0",
        "scipy>=1.11.0",
        "pyyaml>=6.0",
        "pydantic>=2.5.0",
        "sqlalchemy>=2.0.0",
        "fastapi>=0.109.0",
        "uvicorn>=0.27.0",
        "matplotlib>=3.8.0",
        "tqdm>=4.66.0",
    ],
    entry_points={
        "console_scripts": [
            "scc-train=scripts.train_reference:main",
            "scc-live=scripts.run_live_counter:main",
            "scc-analyze=scripts.run_video_analysis:main",
            "scc-dashboard=scripts.run_dashboard:main",
        ],
    },
)
