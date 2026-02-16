import csv
#wq

def show_data_not_corpora():
    file_path = 'notebooks/output/stories_comparison.csv'  # Replace with the actual path to your CSV file

    try:
        with open(file_path, 'r', newline='') as csvfile:
            reader = csv.reader(csvfile)
            # Iterate over each row in the CSV file
            for row in reader:
                if row[3] == "False" and row[7] == "False":   # appears in data and NOT in corpora
                    #print(row)
                    id = row[0].split("/")
                    print(id[5])

    except FileNotFoundError:
        print(f"Error: The file '{file_path}' was not found.")
    except Exception as e:
        print(f"An error occurred: {e}")

show_data_not_corpora()
