from agents.teacher import run_teacher


state = {
    "current_module": 0,
    "current_timestep": 1,

    "curriculum": {
        "modules": [
            {
                "title": "Natural Language Processing",

                "content": """
Introduction to NLP concepts,
sentiment analysis,
language modelling,
and syntactic parsing.
"""
            }
        ]
    }
}


result = run_teacher(state)

print(result["current_lesson"])