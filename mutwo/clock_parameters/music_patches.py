# TODO(Move to mutwo.music)

from mutwo import music_parameters

if 1:

    def ScaleFamily_intersection(
        self, other: music_parameters.ScaleFamily
    ) -> music_parameters.ScaleFamily:
        data = [[], [], [], []]
        for content in zip(
            self.interval_tuple,
            self.weight_tuple,
            self.scale_degree_tuple,
            self.period_repetition_count_tuple,
        ):
            if content[0] in other.interval_tuple:  # content[0] == interval
                for item, list_ in zip(content, data):
                    list_.append(item)
        return music_parameters.ScaleFamily(*data)

    music_parameters.ScaleFamily.intersection = ScaleFamily_intersection

    def Scale_intersection(
        self, other: music_parameters.Scale
    ) -> music_parameters.Scale:
        data = [[], [], [], []]
        for pitch, *content in zip(
            self.pitch_tuple,
            self.scale_family.interval_tuple,
            self.weight_tuple,
            self.scale_degree_tuple,
            self.period_repetition_count_tuple,
        ):
            if content[0] in other.pitch_tuple:  # content[0] == pitch
                for item, list_ in zip(content, data):
                    list_.append(item)
        return music_parameters.Scale(self.tonic, music_parameters.ScaleFamily(*data))

    music_parameters.Scale.intersection = Scale_intersection
