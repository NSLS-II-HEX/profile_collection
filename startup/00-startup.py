

# Begin loading HEX Profile Collection

print('Loading NSLS-II HEX profile collection...')


import time




class FileLoadingTimer:

    def __init__(self, show_time_elapsed=False):
        self.start_time = 0
        self.loading = False
        self.show_time_elapsed = show_time_elapsed


    def start_timer(self, filename):
        if self.loading:
            raise Exception('File already loading!')

        print(f'Loading {filename}...')
        self.start_time = time.time()
        self.loading = True


    def stop_timer(self, filename):

        if not self.loading:
            raise Exception('File was not loading!')

        elapsed = time.time() - self.start_time
        if self.show_time_elapsed:
            print(f'Done loading {filename} in {elapsed} seconds.')
        self.loading = False


file_loading_timer = FileLoadingTimer()