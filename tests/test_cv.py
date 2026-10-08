import numpy as np
import pandas as pd
import pytest

from research.cv import CombinatorialPurgedCV, PurgedKFold, make_label_spans


def _t1(n=100, horizon=5):
    times = pd.date_range("2020-01-01", periods=n, freq="4h")
    return make_label_spans(times, horizon)


def test_label_spans_end_at_horizon():
    t1 = _t1(n=20, horizon=5)
    # rótulo da obs 0 termina no início da barra 5
    assert t1.iloc[0] == t1.index[5]
    # últimas `horizon` obs truncam no fim
    assert t1.iloc[-1] == t1.index[-1]


def test_test_folds_partition_all():
    t1 = _t1()
    cv = PurgedKFold(n_splits=5)
    all_test = np.concatenate([test for _, test in cv.split(t1)])
    assert sorted(all_test.tolist()) == list(range(len(t1)))  # cobre tudo, sem repetir


def test_no_overlap_between_train_and_test():
    t1 = _t1(n=200, horizon=8)
    for train, test in PurgedKFold(n_splits=6).split(t1):
        t_start = t1.index.values[test[0]]
        t_end = t1.values[test].max()
        for j in train:
            s, e = t1.index.values[j], t1.values[j]
            assert e < t_start or s > t_end   # nenhuma sobreposição temporal
        assert not set(train) & set(test)     # disjuntos


def test_embargo_removes_right_neighbors():
    t1 = _t1(n=100, horizon=1)  # sem sobreposição -> só o embargo atua à direita
    no_emb = list(PurgedKFold(n_splits=5, embargo_pct=0.0).split(t1))
    emb = list(PurgedKFold(n_splits=5, embargo_pct=0.10).split(t1))
    # no fold do meio, o treino com embargo é estritamente menor
    tr_no = len(no_emb[2][0])
    tr_emb = len(emb[2][0])
    assert tr_emb < tr_no


def test_invalid_params():
    with pytest.raises(ValueError):
        PurgedKFold(n_splits=1)
    with pytest.raises(ValueError):
        PurgedKFold(embargo_pct=1.0)


def test_cpcv_split_and_path_counts():
    cv = CombinatorialPurgedCV(n_groups=6, n_test_groups=2)
    assert cv.n_splits == 15          # C(6,2)
    assert cv.n_paths == 5            # 2*15/6
    t1 = _t1(n=120, horizon=3)
    splits = list(cv.split(t1))
    assert len(splits) == 15


def test_cpcv_no_overlap_and_every_obs_tested():
    n, n_groups = 150, 5
    t1 = _t1(n=n, horizon=6)
    groups = np.array_split(np.arange(n), n_groups)
    cv = CombinatorialPurgedCV(n_groups=n_groups, n_test_groups=2)
    tested = set()
    for train, test in cv.split(t1):
        assert not set(train) & set(test)
        test_set = set(test.tolist())
        test_groups = [g for g in groups if set(g.tolist()) <= test_set]
        for g in test_groups:                       # nenhum treino sobrepõe o span de CADA grupo de teste
            gs, ge = t1.index.values[g[0]], t1.values[g].max()
            for j in train:
                s, e = t1.index.values[j], t1.values[j]
                assert e < gs or s > ge
        tested |= test_set
    assert tested == set(range(n))                  # todo obs é testado em algum caminho


def test_cpcv_invalid_params():
    with pytest.raises(ValueError):
        CombinatorialPurgedCV(n_groups=4, n_test_groups=4)
    with pytest.raises(ValueError):
        CombinatorialPurgedCV(n_groups=4, n_test_groups=1)
