
from src.generator.config import DatasetConfig
from src.analyze.functions import check_static_determinacy, split_in_base_systems
from problem_definitions import *
from src.GUIs.main_GUI import MainWindow
import run


def test_verlauf_checker():
    #definition = einfeld_traeger()
    #definition = einspannung()
    #definition = complex_problem()
    definition = complex_problem_v2()


    f = check_static_determinacy(definition)
    print(f"Degree of static indeterminacy: {f}")
    if f == 0:
        split_in_base_systems(definition)
    else:
        print("The system is not statically determinate, cannot calculate reaction forces.")



def test_generate_dataset():
    from src.generator.generate import generate_sample_dataset
    from src.generator.yolo import visualize_yolo_dataset
    dataset = generate_sample_dataset()
    visualize_yolo_dataset(dataset)

def test_visualize_dataset():
    from src.generator.yolo import YOLODatasetManager, visualize_yolo_dataset
    visualize_yolo_dataset(r"C:\Users\Johan\Documents\programme\Statik\datasets\structures\dataset.yaml",
                       split="val", shuffle=True, invert_y=False)
def test_visualize_gallery():
    from src.generator.generate import visualize_test_GALLERIES
    visualize_test_GALLERIES()

def test_train():
    from src.vision.trainer import YOLOTrainer
    config = DatasetConfig()
    trainer = YOLOTrainer(config)
    trainer.train(epochs=5, batch_size=8, learning_rate=0.001)


if __name__ == "__main__":
    #test_start_GUI()
    test_generate_dataset()
    #test_visualize_dataset()
    #server.app.run(host="127.0.0.1", port=5000, debug=True)