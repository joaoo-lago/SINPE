"""Prova de que o motor estatístico escolhe e roda o teste certo.

Reproduz o espírito dos gráficos do TCC (sexo, diagnóstico, faixa etária).
Rode com: pytest backend/tests/test_stats_engine.py
"""
import pandas as pd

from app.stats import engine as stats


def test_categorical_vs_categorical_usa_qui_quadrado():
    df = pd.DataFrame({
        "sexo": ["M", "F", "M", "F", "M", "F", "M", "F", "M", "F"] * 6,
        "diagnostico": (["HAS"] * 6 + ["IAM"] * 4) * 6,
    })
    res = stats.analyze(df, "sexo", "diagnostico")
    assert res.test is not None
    assert "Qui-quadrado" in res.test.test_name or "Fisher" in res.test.test_name
    assert res.chart.kind == "grouped_bar"


def test_categorical_vs_numeric_duas_categorias_usa_t_ou_mannwhitney():
    df = pd.DataFrame({
        "grupo": ["A"] * 15 + ["B"] * 15,
        "idade": list(range(40, 55)) + list(range(60, 75)),
    })
    res = stats.analyze(df, "grupo", "idade")
    assert res.test is not None
    assert res.test.test_name in ("t-Student (Welch)", "Mann-Whitney U")
    assert res.chart.kind == "bar"


def test_numeric_vs_numeric_usa_correlacao():
    df = pd.DataFrame({"x": range(30), "y": [i * 2 + 1 for i in range(30)]})
    res = stats.analyze(df, "x", "y", kind_x="numeric", kind_y="numeric")
    assert res.test is not None
    assert "Correlação" in res.test.test_name
    assert res.test.p_value is not None and res.test.p_value < 0.05


def test_describe_categorico_traz_frequencias():
    s = pd.Series(["M", "M", "F", "indefinido"])
    d = stats.describe(s)
    assert d["n"] == 4
    assert d["frequencias"]["M"]["contagem"] == 2
    assert d["frequencias"]["M"]["percentual"] == 50.0
