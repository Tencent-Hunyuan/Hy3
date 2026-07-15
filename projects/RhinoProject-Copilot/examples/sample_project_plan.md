# Sample Project Plan Output

## Project Name

RhinoProject Copilot

## Project Positioning

RhinoProject Copilot is an AI-powered assistant for student developers who are participating in open-source training programs, innovation competitions, course projects, or research practice tasks.

The project helps users transform a vague GitHub Issue or project idea into a structured and executable project plan.

## Target Users

- University students participating in open-source training programs
- Beginners who are not familiar with GitHub Issues
- Student teams preparing innovation or entrepreneurship projects
- Course project teams that need README and presentation materials
- Developers who need quick project planning support

## Core Scenario

A student sees a GitHub Issue but does not know how to start.

The student pastes the Issue into RhinoProject Copilot. The system then generates:

1. Issue analysis
2. Project proposal
3. Development route
4. README outline
5. PPT / defense outline
6. Project quality evaluation

## Core Features

| Feature | Output |
|---|---|
| Issue Analysis | Task goal, requirements, technical keywords, deliverables |
| Project Proposal | Project positioning, target users, features, tech stack |
| Development Plan | Step-by-step development tasks |
| README Generation | Markdown project documentation |
| PPT Outline | Presentation structure and defense script |
| Quality Evaluation | Rubric-based self-assessment |

## Technical Route

1. Build a Streamlit frontend.
2. Design multiple task modes.
3. Store reusable prompt templates.
4. Call Hy3-preview through an OpenAI-compatible API.
5. Render results in Markdown.
6. Provide Markdown download.
7. Prepare README, examples, screenshot, and configuration files.

## MVP Version

The MVP version includes:

- Streamlit UI
- Demo Mode
- Issue analysis
- Project proposal generation
- README generation
- PPT outline generation
- Project quality evaluation
- Example input and output
- README documentation
- Local run screenshot

## Hy3-preview Role

Hy3-preview is responsible for:

- understanding long GitHub Issue text;
- extracting key project requirements;
- generating structured project plans;
- creating README and PPT outlines;
- evaluating project quality with rubric-style output.

## Expected Value

RhinoProject Copilot lowers the barrier for student developers to participate in open-source contribution. It provides a practical workflow from requirement understanding to project delivery.

## Future Improvements

- GitHub Issue URL auto-fetching
- More project templates
- Multi-file repository analysis
- PPT export
- Project quality score visualization
