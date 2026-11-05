"""One-dimensional K-Means, independent of the presentation UI."""
POINTS = {
    "A": 10.0, "B": 10.4, "C": 10.9, "D": 11.3, "E": 11.5,
    "F": 11.7, "G": 12.1, "H": 12.6, "I": 13.0,
}
INITIAL = (10.0, 11.7)


def distances(point, centroids):
    return [(point - center) ** 2 for center in centroids]


def assign(centroids):
    # Deterministic ties go to the first (blue) centroid.
    return {name: min(range(len(centroids)), key=lambda i: distances(value, centroids)[i])
            for name, value in POINTS.items()}


def move(labels, previous):
    result = []
    for cluster, center in enumerate(previous):
        members = [value for name, value in POINTS.items() if labels[name] == cluster]
        result.append(sum(members) / len(members) if members else center)
    return tuple(result)


def make_stages(initial=INITIAL):
    centers = initial
    stages = [("Starting point", None, centers,
               "Each point has ONE numerical value. Stars show the two initial centroids.")]
    previous = None
    for iteration in range(1, 101):
        labels = assign(centers)
        if labels == previous:
            stages.append(("Convergence", labels, centers,
                           "Reassigning changes nothing. Both centroids are their cluster means; K-Means stops."))
            return stages
        changed = [n for n in POINTS if previous is not None and labels[n] != previous[n]]
        explanation = "Assign each value to its nearest centroid (smallest absolute distance)."
        if changed:
            explanation = "Updated centroids change the nearest group for: " + ", ".join(changed) + "."
        stages.append((f"Assign points · round {iteration}", labels, centers, explanation))
        centers = move(labels, centers)
        stages.append((f"Move centroids · round {iteration}", labels, centers,
                       "Each centroid moves to the arithmetic mean of the values in its cluster."))
        previous = labels
    raise RuntimeError("K-Means did not converge within 100 iterations")


STAGES = make_stages()
