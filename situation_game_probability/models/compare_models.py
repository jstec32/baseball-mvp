import pickle
import os
import pandas as pd
import matplotlib
matplotlib.use("Agg") 
import matplotlib.pyplot as plt
import seaborn as sns
from sklearn.metrics import classification_report, confusion_matrix, roc_curve, auc
from sklearn.preprocessing import label_binarize

# Configuration
DATA_DIR = "/Users/joshsteckler/PycharmProjects/baseball-mvp/situation_game_probability/data"
FILES = {
    "Elastic Net (w/ Season Stats)": "results_elastic_net.pkl",
    "Elastic Net (Original)": "results_elastic_net_original.pkl"
}

summary = []
roc_data = {}

# load and evaluate versions
for model_name, file_name in FILES.items():
    result_path = os.path.join(DATA_DIR, file_name)
    with open(result_path, "rb") as f:
        results = pickle.load(f)

    print(f"\n{model_name}")
    print(f"Accuracy:  {results['accuracy']:.4f}")
    print(f"Log Loss:  {results['log_loss']:.4f}")
    print(f"AUC (OvR): {results['auc_ovr']:.4f}")

    print("\nClassification Report:")
    print(classification_report(results["y_true"], results["y_pred"], target_names=results["target_names"]))

    print("\nConfusion Matrix:")
    print(confusion_matrix(results["y_true"], results["y_pred"]))

    summary.append({
        "Model": model_name,
        "Accuracy": results["accuracy"],
        "Log Loss": results["log_loss"],
        "AUC (OvR)": results["auc_ovr"]
    })

    # Prepare for ROC curve
    y_true_bin = label_binarize(results["y_true"], classes=list(range(len(results["target_names"]))))
    roc_data[model_name] = {
        "y_true": y_true_bin,
        "y_proba": results.get("y_proba"),
        "target_names": results["target_names"]
    }

# --- Leaderboard ---
df_summary = pd.DataFrame(summary)
print("\nCompare Elastic Net Versions")
print(df_summary.to_string(index=False))

# --- Bar Chart Comparison ---
plt.figure(figsize=(10, 5))
sns.barplot(
    data=df_summary.melt(id_vars="Model", value_vars=["Accuracy", "Log Loss", "AUC (OvR)"]),
    x="Model", y="value", hue="variable"
)
plt.title("Elastic Net Comparison: With vs. Without Season Stats")
plt.ylabel("Score")
plt.tight_layout()
plt.close(fig)

# --- ROC Curves per class ---
plt.figure(figsize=(10, 8))
colors = ["blue", "green"]
for i, (model_name, roc) in enumerate(roc_data.items()):
    y_true_bin = roc["y_true"]
    y_proba = roc["y_proba"]
    if y_proba is None:
        continue

    for class_idx in range(y_true_bin.shape[1]):
        fpr, tpr, _ = roc_curve(y_true_bin[:, class_idx], y_proba[:, class_idx])
        roc_auc = auc(fpr, tpr)
        label = f"{model_name} - {roc['target_names'][class_idx]} (AUC={roc_auc:.2f})"
        plt.plot(fpr, tpr, label=label, color=colors[i], alpha=0.3 + 0.2 * class_idx)

plt.plot([0, 1], [0, 1], 'k--', label="Random")
plt.title("ROC Curves by Outcome Class (Elastic Net Versions)")
plt.xlabel("False Positive Rate")
plt.ylabel("True Positive Rate")
plt.legend(loc="lower right", fontsize=8)
plt.tight_layout()
plt.close(fig)

