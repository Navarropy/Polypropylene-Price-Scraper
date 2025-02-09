import normalization
import diagram
import mra
import forecast  # <-- import your Prophet script

if __name__ == '__main__':
    # 1) Normalize
    normalization.process_folder('data', 'normalized_files')
    print("\nNormalization complete!")
    
    # 2) Continuous Wavelet Diagrams from normalized
    diagram.generate_diagrams('normalized_files', 'diagrams')
    print("\nAll continuous wavelet diagrams generated successfully!")

    # 3) MRA from normalized
    mra.generate_mra_all_files(
        data_folder='normalized_files',
        output_folder='mra_diagrams'
    )
    print("\nAll MRA diagrams generated successfully!")

    # 4) Prophet Forecast Diagrams from normalized
    forecast.generate_forecasts(
        normalized_folder='normalized_files',
        output_folder='regression_plots',
        forecast_periods=12
    )
    print("\nAll Prophet forecasts generated successfully!")
