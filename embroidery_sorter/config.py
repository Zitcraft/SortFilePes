"""
Configuration settings for embroidery sorter
"""

class Config:
    """Configuration class for embroidery sorting parameters"""
    
    # Time estimation parameters
    STITCHES_PER_MINUTE = 800.0
    COLOR_CHANGE_SECONDS = 120.0
    TRIM_SECONDS = 3
    JUMP_SECONDS = 0.2
    
    # Duplicate reduction
    DUPLICATE_REDUCTION_SECONDS = 300.0  # 5 minutes
    
    # Assignment parameters
    DEFAULT_PEOPLE_COUNT = 4
    DEFAULT_PERSON_LABELS = ["A", "B", "C", "D"]
    # Person weights - last person gets less work (0.2 = 20% of normal workload)
    DEFAULT_PERSON_WEIGHTS = [1.0, 1.0, 0.7, 0.2]
    
    # File operation parameters
    DEFAULT_HASH_LENGTH = 8
    FOLDER_INDEX_FORMAT = "{:03d}"
    
    # Stitch command codes
    TRIM_CODE = 2
    JUMP_CODE = 1
    
    # Timestamp format
    TIMESTAMP_FORMAT = "%Y-%m-%d_%H-%M-%S"
    
    @classmethod
    def get_time_params(cls):
        """Get time estimation parameters as dict"""
        return {
            'stitches_per_minute': cls.STITCHES_PER_MINUTE,
            'color_change_seconds': cls.COLOR_CHANGE_SECONDS,
            'trim_seconds': cls.TRIM_SECONDS,
            'jump_seconds': cls.JUMP_SECONDS
        }
    
    @classmethod
    def get_assignment_params(cls):
        """Get assignment parameters as dict"""
        return {
            'people_count': cls.DEFAULT_PEOPLE_COUNT,
            'person_labels': cls.DEFAULT_PERSON_LABELS,
            'person_weights': cls.DEFAULT_PERSON_WEIGHTS,
            'duplicate_reduction': cls.DUPLICATE_REDUCTION_SECONDS
        }