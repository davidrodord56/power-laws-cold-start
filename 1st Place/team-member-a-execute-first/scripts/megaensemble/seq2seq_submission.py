"""
Submission of all the frankenstein models
"""
import os
import glob
import pandas as pd

from coldstart.definitions import DATASET_PATH
from coldstart.seq2seq.model import MetaModel, load_model
from coldstart.seq2seq.data import prepare_x
from coldstart.seq2seq.train_manager import TrainManager
from coldstart.utils import load_data

def main():
    model_dirs = glob.glob(
        '/media/guillermo/Data/DrivenData/Cold_Start/models/2018_10_29_seq2seq/*')
    train_manager = TrainManager(4)
    for model_dir in model_dirs:
        train_manager.submit(create_submission, model_dir)


def create_submission(model_dir):
    submission_path = os.path.join(
        DATASET_PATH, 'submissions', '20181029_seq2seq', '%s.csv' % os.path.basename(model_dir))
    if os.path.exists(submission_path):
        return
    meta_model = _load_meta_model(model_dir)

    _, test, submission, metadata = load_data()

    test_preds = {}
    submission_series_id = submission[submission.prediction_window == 'hourly'].series_id.unique()
    for series_id in submission_series_id:
        window = submission[submission.series_id == series_id].prediction_window.values[0]
        df = test[test.series_id == series_id].copy()
        df.reset_index(inplace=True)
        if len(df) > 7*24:
            df = df.loc[len(df)-7*24:]
        x, mean_value, next_day = prepare_x(window, df, metadata, series_id)
        pred = meta_model.predict(x, window, next_day)*mean_value
        test_preds[series_id] = pred[0, :, 0]

    base_submission = pd.read_csv(DATASET_PATH + '/submissions/20181027_average.csv')

    new_consumption = base_submission.consumption.values.copy()
    submission_series_id = base_submission.series_id.values

    for series_id in test_preds:
        new_consumption[submission_series_id == series_id] = test_preds[series_id]

    new_submission = base_submission.copy()
    new_submission['consumption'] = new_consumption
    new_submission.to_csv(submission_path, index=False)
    print(os.path.basename(submission_path))

def _load_meta_model(model_dir):
    meta_model = MetaModel()
    window = 'hourly'
    for input_days in range(1, 8):
        for is_working in range(2):
            model_path = os.path.join(model_dir, '%s_%i_working%i.h5' % (window, input_days, is_working))
            model = load_model(model_path)
            meta_model.models[window][input_days][is_working] = model
    return meta_model

if __name__ == '__main__':
    main()
