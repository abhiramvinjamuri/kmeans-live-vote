# Human vs K-Means: classroom voting

Nine single-number values: **10.0, 10.4, 10.9, 11.3, 11.5, 11.7, 12.1, 12.6, 13.0**.
Letters A-I identify values, not extra features. K=2, with initial centers 10.0 and 11.7.
The center values are deliberately asymmetrical so C changes from Orange to Blue.
The app calculates the six reveal stages from the dataset rather than hard-coding a story.

## Presenter access

Open the audience app address with `?role=presenter` appended. Enter your private presenter password.
The audience address has no query string. Students do not need the presenter password.

1. Paste the public app address into **Audience link and QR code**; download or project the QR.
2. Assign students unique seat numbers from 1 to 60.
3. Click **Open voting**, then share the audience link.
4. Click **Close voting**, then **Reveal class results**.
5. Click **Next** to walk through assign, move, reassign, move and convergence.
6. Download the vote totals CSV before ending the class.
7. Use **Start a new round** for another class. It clears the displayed totals, retains old rounds in the local database and closes voting until reopened.

## Local run

Install requirements with `python -m pip install -r requirements.txt`.
Create `.streamlit/secrets.toml` containing `ADMIN_PASSWORD = "your-private-password"`.
Run `python -m streamlit run app.py` from this directory.
Audience: http://localhost:8501/
Presenter: http://localhost:8501/?role=presenter
The localhost address works only on the host computer.

## Deployment

Deploy this repository on Streamlit Community Cloud, branch `main`, entrypoint `app.py`.
Set ADMIN_PASSWORD in Advanced settings / Secrets before deploying.
Keep `.streamlit/secrets.toml`, vote databases, and passwords out of GitHub.
Public audience access and password-protected presenter controls are separate settings.

Community Cloud local storage is not guaranteed to persist across restarts or redeployments.
Export totals after the class; this is an informal classroom activity. Seat numbers are not identity verification.
A concurrent 60-ballot database test passes locally; test the deployed app on a few phones before class.

## Teaching details

Close absolute values alone do not mathematically make K-Means harder: shifting or uniformly scaling a dataset preserves its assignments. This dataset places several values near possible split points and avoids a large obvious gap. Students vote on nearest INITIAL centers; the final result can differ after centers move. Agreement with final clusters is a comparison, not a grading score.

Distance is absolute difference (or squared difference, which gives the same nearest center). Centroids are arithmetic means. Exact ties go to Blue. Empty clusters retain their previous center.

## Files and checks

- app.py: audience and presenter screens
- model.py: values and K-Means stages
- storage.py: shared SQLite votes, atomic closure checks and round isolation
- test_app.py: algorithm, duplicate, closed, invalid, stale and concurrent-ballot tests

Run `python -m unittest -v test_app.py`.
