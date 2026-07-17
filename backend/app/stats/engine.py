"""Motor estatístico do SINPE.

Recebe um DataFrame (uma coluna por variável, formato largo) e duas variáveis,
inspeciona os tipos e a cardinalidade, e escolhe automaticamente o teste correto:

    categórica  × categórica         -> Qui-quadrado (ou Fisher se amostra pequena)
    categórica  × numérica (2 grupos) -> t-Student (ou Mann-Whitney se não-normal)
    categórica  × numérica (3+ grupos)-> ANOVA (ou Kruskal-Wallis)
    numérica    × numérica            -> Pearson (ou Spearman)

Também produz as séries prontas para gráficos de barra/pizza no front-end.
Toda a matemática mora aqui; o front só desenha.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Literal

import numpy as np
import pandas as pd
from scipy import stats

VarKind = Literal["categorical", "numeric"]


@dataclass
class ChartSeries:
    """Dados prontos para o front desenhar barra ou pizza."""

    kind: Literal["bar", "pie", "grouped_bar"]
    labels: list[str]
    values: list[float]
    series_name: str = ""
    groups: dict[str, list[float]] = field(default_factory=dict)  # para grouped_bar


@dataclass
class TestResult:
    test_name: str
    statistic: float | None
    p_value: float | None
    effect_size: float | None
    effect_label: str
    n: int
    interpretation: str
    assumptions: dict[str, Any] = field(default_factory=dict)


@dataclass
class AnalysisResult:
    chart: ChartSeries
    test: TestResult | None


def infer_kind(series: pd.Series, declared: VarKind | None = None) -> VarKind:
    """Decide se a variável é categórica ou numérica (respeitando declaração explícita)."""
    if declared:
        return declared
    if pd.api.types.is_numeric_dtype(series) and series.nunique(dropna=True) > 10:
        return "numeric"
    return "categorical"


ALPHA = 0.05


def _cramers_v(chi2: float, table: pd.DataFrame) -> float:
    """Tamanho de efeito para qui-quadrado."""
    n = table.to_numpy().sum()
    if n == 0:
        return 0.0
    k = min(table.shape) - 1
    return float(np.sqrt(chi2 / (n * k))) if k > 0 else 0.0


def _cohens_d(a: np.ndarray, b: np.ndarray) -> float:
    """Tamanho de efeito para t-Student (duas amostras)."""
    na, nb = len(a), len(b)
    if na < 2 or nb < 2:
        return 0.0
    pooled = np.sqrt(((na - 1) * a.var(ddof=1) + (nb - 1) * b.var(ddof=1)) / (na + nb - 2))
    return float((a.mean() - b.mean()) / pooled) if pooled else 0.0


def analyze(
    df: pd.DataFrame,
    var_x: str,
    var_y: str,
    kind_x: VarKind | None = None,
    kind_y: VarKind | None = None,
) -> AnalysisResult:
    """Ponto de entrada: cruza var_x e var_y, escolhe o teste e devolve gráfico + resultado."""
    data = df[[var_x, var_y]].dropna()
    kx = infer_kind(data[var_x], kind_x)
    ky = infer_kind(data[var_y], kind_y)

    if kx == "categorical" and ky == "categorical":
        return _categorical_vs_categorical(data, var_x, var_y)
    if kx == "numeric" and ky == "numeric":
        return _numeric_vs_numeric(data, var_x, var_y)
    # um categórico, um numérico
    cat, num = (var_x, var_y) if kx == "categorical" else (var_y, var_x)
    return _categorical_vs_numeric(data, cat, num)


def _categorical_vs_categorical(df: pd.DataFrame, x: str, y: str) -> AnalysisResult:
    table = pd.crosstab(df[x], df[y])
    n = int(table.to_numpy().sum())

    chart = ChartSeries(
        kind="grouped_bar",
        labels=list(table.index.astype(str)),
        values=[],
        series_name=f"{x} × {y}",
        groups={str(col): table[col].tolist() for col in table.columns},
    )

    if table.shape == (2, 2) and n < 40:
        _, p = stats.fisher_exact(table.to_numpy())
        test = TestResult(
            test_name="Teste exato de Fisher",
            statistic=None, p_value=float(p), effect_size=None,
            effect_label="", n=n,
            interpretation=_interp(p),
        )
    else:
        chi2, p, dof, _ = stats.chi2_contingency(table)
        v = _cramers_v(chi2, table)
        test = TestResult(
            test_name="Qui-quadrado de Pearson",
            statistic=float(chi2), p_value=float(p),
            effect_size=v, effect_label="V de Cramér", n=n,
            interpretation=_interp(p),
            assumptions={"graus_de_liberdade": int(dof)},
        )
    return AnalysisResult(chart=chart, test=test)


def _categorical_vs_numeric(df: pd.DataFrame, cat: str, num: str) -> AnalysisResult:
    groups = [g[num].to_numpy() for _, g in df.groupby(cat) if len(g) > 0]
    labels = [str(k) for k, g in df.groupby(cat) if len(g) > 0]
    n = int(len(df))

    chart = ChartSeries(
        kind="bar",
        labels=labels,
        values=[float(np.mean(g)) for g in groups],
        series_name=f"Média de {num} por {cat}",
    )

    # pressupostos: normalidade (Shapiro) por grupo
    normal = all(len(g) < 3 or stats.shapiro(g).pvalue > ALPHA for g in groups)

    if len(groups) == 2:
        if normal:
            statv, p = stats.ttest_ind(groups[0], groups[1], equal_var=False)
            d = _cohens_d(groups[0], groups[1])
            test = TestResult("t-Student (Welch)", float(statv), float(p), d, "d de Cohen", n, _interp(p),
                              {"normalidade_ok": True})
        else:
            statv, p = stats.mannwhitneyu(groups[0], groups[1])
            test = TestResult("Mann-Whitney U", float(statv), float(p), None, "", n, _interp(p),
                              {"normalidade_ok": False})
    elif len(groups) >= 3:
        if normal:
            statv, p = stats.f_oneway(*groups)
            test = TestResult("ANOVA de uma via", float(statv), float(p), None, "", n, _interp(p),
                              {"normalidade_ok": True})
        else:
            statv, p = stats.kruskal(*groups)
            test = TestResult("Kruskal-Wallis", float(statv), float(p), None, "", n, _interp(p),
                              {"normalidade_ok": False})
    else:
        test = None
    return AnalysisResult(chart=chart, test=test)


def _numeric_vs_numeric(df: pd.DataFrame, x: str, y: str) -> AnalysisResult:
    n = int(len(df))
    normal = (
        (len(df) < 3 or stats.shapiro(df[x]).pvalue > ALPHA)
        and (len(df) < 3 or stats.shapiro(df[y]).pvalue > ALPHA)
    )
    if normal:
        r, p = stats.pearsonr(df[x], df[y])
        name, label = "Correlação de Pearson", "r"
    else:
        r, p = stats.spearmanr(df[x], df[y])
        name, label = "Correlação de Spearman", "ρ"

    chart = ChartSeries(
        kind="bar",  # o front pode plotar como dispersão usando os pontos brutos
        labels=[str(v) for v in df[x].tolist()],
        values=df[y].tolist(),
        series_name=f"{y} vs {x}",
    )
    test = TestResult(name, float(r), float(p), float(r), label, n, _interp(p))
    return AnalysisResult(chart=chart, test=test)


def _interp(p: float) -> str:
    if p < ALPHA:
        return f"Diferença/associação estatisticamente significativa (p = {p:.4f} < {ALPHA})."
    return f"Sem significância estatística ao nível de {ALPHA} (p = {p:.4f})."


def describe(series: pd.Series) -> dict[str, Any]:
    """Estatística descritiva básica (média, frequência) — como o TCC faz."""
    if pd.api.types.is_numeric_dtype(series):
        return {
            "n": int(series.count()),
            "media": float(series.mean()),
            "desvio_padrao": float(series.std(ddof=1)) if series.count() > 1 else 0.0,
            "minimo": float(series.min()),
            "maximo": float(series.max()),
            "mediana": float(series.median()),
        }
    counts = series.value_counts()
    total = int(counts.sum())
    return {
        "n": total,
        "frequencias": {
            str(k): {"contagem": int(v), "percentual": round(100 * v / total, 2)}
            for k, v in counts.items()
        },
    }
