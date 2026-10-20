from .curve_editor_curve_items import *

infinity_line_length = 10000  # not visually infinity in current implementation


class InfinityCurveModel:
    def __init__(self):
        self._segment_list = []
        self._anchor_rects = []
        self._step_rects = []  # it should be empty or the same len as _segment_list.


class InfinityCurveAnchorUpdater:
    def __init__(self, model_list):
        self._model_list = model_list

    def get_model_quantity(self):
        return len(self._model_list)

    def update_model(self, parent_curve, index, model_index, ui_offset_x_bias, ui_offset_y_bias):
        self.update_model_x(parent_curve, index, model_index, ui_offset_x_bias)
        self.update_model_y(parent_curve, index, model_index, ui_offset_y_bias)

    def update_model_x(self, parent_curve, index, model_index, ui_offset_x_bias):
        offset_x = parent_curve._key_rects[index].get_key_ui_x() + ui_offset_x_bias
        self._model_list[model_index]._anchor_rects[index]._set_ui_x(offset_x)
        if index > 0:
            self._model_list[model_index]._step_rects[index - 1]._set_ui_x(offset_x)

    def update_model_y(self, parent_curve, index, model_index, ui_offset_y_bias):
        offset_y = parent_curve._key_rects[index].get_key_ui_y() + ui_offset_y_bias
        self._model_list[model_index]._anchor_rects[index]._set_ui_y(offset_y)
        if index < parent_curve._get_segment_quantity():
            self._model_list[model_index]._step_rects[index]._set_ui_y(offset_y)

    def update_mirror_model_x(self, parent_curve, index, model_index, ui_offset_x_aggregated):
        offset_x = ui_offset_x_aggregated - parent_curve._key_rects[index].get_key_ui_x()
        self._model_list[model_index]._anchor_rects[index]._set_ui_x(offset_x)
        if index > 0:
            self._model_list[model_index]._step_rects[index - 1]._set_ui_x(offset_x)  # temptest

    def update_mirror_model_y(self, parent_curve, index, model_index):
        # the same as non mirror behavior for y
        self.update_model_y(parent_curve, index, model_index, 0)

    def update_mirror_model(self, parent_curve, index, model_index, ui_offset_x_aggregated):
        self.update_mirror_model_x(parent_curve, index, model_index, ui_offset_x_aggregated)
        self.update_mirror_model_y(parent_curve, index, model_index)

    # for linear model and constant model only.
    def _set_anchor_ui_offset(self, parent_curve, index, ui_offset_x_bias, ui_offset_y_bias, anchor_index):
        offset_x = parent_curve._key_rects[index].get_key_ui_x() + ui_offset_x_bias
        offset_y = parent_curve._key_rects[index].get_key_ui_y() + ui_offset_y_bias
        self._model_list[0]._anchor_rects[anchor_index]._set_ui_x(offset_x)
        self._model_list[0]._anchor_rects[anchor_index]._set_ui_y(offset_y)

    def update_linear_pre_model(self, parent_curve):
        if len(parent_curve._segment_list) > 0:
            ui_bezier_segment = parent_curve._segment_list[0]._ui_bezier_segment
            start_tangent_width, start_tangent_height, end_tangent_width, end_tangent_height = get_ui_bezier_tangent(
                ui_bezier_segment
            )
        else:
            # special case for curve with only one key
            start_tangent_width, start_tangent_height = 0, 0

        r = math.sqrt(start_tangent_width * start_tangent_width + start_tangent_height * start_tangent_height)
        # take 0.001 as threshold. Too small I take direction as not meaningful.
        neg_R_div_r = (-infinity_line_length / r) if r > 0.001 else 0
        tw = neg_R_div_r * start_tangent_width
        th = neg_R_div_r * start_tangent_height

        self._set_anchor_ui_offset(parent_curve, 0, tw, th, 0)
        self._set_anchor_ui_offset(parent_curve, 0, 0.0, 0.0, 1)

    def update_linear_post_model(self, parent_curve):
        if len(parent_curve._segment_list) > 0:
            ui_bezier_segment = parent_curve._segment_list[-1]._ui_bezier_segment
            start_tangent_width, start_tangent_height, end_tangent_width, end_tangent_height = get_ui_bezier_tangent(
                ui_bezier_segment
            )
        else:
            # special case for curve with only one key
            end_tangent_width, end_tangent_height = 0, 0

        r = math.sqrt(end_tangent_width * end_tangent_width + end_tangent_height * end_tangent_height)
        # take 0.001 as threshold. Too small I take direction as not meaningful.
        neg_R_div_r = (-infinity_line_length / r) if r > 0.001 else 0
        tw = neg_R_div_r * end_tangent_width
        th = neg_R_div_r * end_tangent_height

        self._set_anchor_ui_offset(parent_curve, -1, 0.0, 0.0, 0)
        self._set_anchor_ui_offset(parent_curve, -1, tw, th, 1)

    def update_constant_pre_model(self, parent_curve):
        self._set_anchor_ui_offset(parent_curve, 0, -infinity_line_length, 0.0, 0)
        self._set_anchor_ui_offset(parent_curve, 0, 0.0, 0.0, 1)

    def update_constant_post_model(self, parent_curve):
        self._set_anchor_ui_offset(parent_curve, -1, 0.0, 0.0, 0)
        self._set_anchor_ui_offset(parent_curve, -1, infinity_line_length, 0.0, 1)


class InfinityCurveSegmentUpdater:
    def __init__(self, model_list):
        self._model_list = model_list

    def get_model_quantity(self):
        return len(self._model_list)

    def update_model(self, parent_curve, index, model_index):
        ui_bezier_segment = parent_curve._segment_list[index]._ui_bezier_segment
        start_tangent_width, start_tangent_height, end_tangent_width, end_tangent_height = get_ui_bezier_tangent(
            ui_bezier_segment
        )
        self._model_list[model_index]._segment_list[index].update_ui_tangent(
            start_tangent_width, start_tangent_height, end_tangent_width, end_tangent_height
        )

    def update_mirror_model(self, parent_curve, index, model_index):
        ui_bezier_segment = parent_curve._segment_list[index]._ui_bezier_segment
        start_tangent_width, start_tangent_height, end_tangent_width, end_tangent_height = get_ui_bezier_tangent(
            ui_bezier_segment
        )
        self._model_list[model_index]._segment_list[index].update_ui_tangent(
            -float(start_tangent_width), start_tangent_height, -float(end_tangent_width), end_tangent_height
        )

    def update_by_visibility(self, parent_curve, index, model_index):
        is_bezier_visible = parent_curve._segment_list[index]._ui_bezier_segment.visible
        self._model_list[model_index]._segment_list[index].show_as_bezier(is_bezier_visible)


class InfinityCurveUpdater:
    def __init__(self, model_list):
        self._model_list = model_list

    def get_model_quantity(self):
        return len(self._model_list)

    def update_model(self, parent_curve, model_index, ui_offset_x_bias, ui_offset_y_bias):
        for index in range(parent_curve._get_key_quantity()):
            InfinityCurveAnchorUpdater(self._model_list).update_model(
                parent_curve, index, model_index, ui_offset_x_bias, ui_offset_y_bias
            )
        for index in range(parent_curve._get_segment_quantity()):
            InfinityCurveSegmentUpdater(self._model_list).update_model(parent_curve, index, model_index)

    def update_mirror_model(self, parent_curve, model_index, ui_offset_x_aggregated):
        for index in range(parent_curve._get_key_quantity()):
            InfinityCurveAnchorUpdater(self._model_list).update_mirror_model(
                parent_curve, index, model_index, ui_offset_x_aggregated
            )
        for index in range(parent_curve._get_segment_quantity()):
            InfinityCurveSegmentUpdater(self._model_list).update_mirror_model(parent_curve, index, model_index)

    def update_linear_pre_model(self, parent_curve):
        # segment tangents do not need to update, just update anchors.
        InfinityCurveAnchorUpdater(self._model_list).update_linear_pre_model(parent_curve)

    def update_linear_post_model(self, parent_curve):
        # segment tangents do not need to update, just update anchors.
        InfinityCurveAnchorUpdater(self._model_list).update_linear_post_model(parent_curve)

    def update_constant_pre_model(self, parent_curve):
        # segment tangents do not need to update, just update anchors.
        InfinityCurveAnchorUpdater(self._model_list).update_constant_pre_model(parent_curve)

    def update_constant_post_model(self, parent_curve):
        # segment tangents do not need to update, just update anchors.
        InfinityCurveAnchorUpdater(self._model_list).update_constant_post_model(parent_curve)


class InfinityCurveBuilder:
    def __init__(self):
        self._model_list = []

    def get_model_list(self):
        return self._model_list

    def build_model(self, parent_curve, ui_offset_x_bias, ui_offset_y_bias):
        model = InfinityCurveModel()
        for origin_key_rect in parent_curve._key_rects:
            self._build_anchor(origin_key_rect, ui_offset_x_bias, ui_offset_y_bias, model._anchor_rects)
        for origin_control_segment in parent_curve._segment_list:
            self._build_segment(origin_control_segment, model._anchor_rects, model._step_rects, model._segment_list)

        self._model_list.append(model)

    def build_mirror_model(self, parent_curve, ui_offset_x_aggregated):
        model = InfinityCurveModel()
        for origin_key_rect in parent_curve._key_rects:
            self._build_mirror_anchor(origin_key_rect, ui_offset_x_aggregated, model._anchor_rects)
        for origin_control_segment in parent_curve._segment_list:
            self._build_mirror_segment(
                origin_control_segment, model._anchor_rects, model._step_rects, model._segment_list
            )

        self._model_list.append(model)

    def build_constant_pre_model(self, parent_curve):
        model = InfinityCurveModel()
        self._build_line_segment(parent_curve, model)

        # do it before later update which needs self._model_list.
        self._model_list.append(model)

        # update anchors offset
        updater = InfinityCurveUpdater(self._model_list)
        updater.update_constant_pre_model(parent_curve)

    def build_constant_post_model(self, parent_curve):
        model = InfinityCurveModel()
        self._build_line_segment(parent_curve, model)

        # do it before later update which needs self._model_list.
        self._model_list.append(model)

        # update anchors offset
        updater = InfinityCurveUpdater(self._model_list)
        updater.update_constant_post_model(parent_curve)

    def build_linear_pre_model(self, parent_curve):
        model = InfinityCurveModel()
        self._build_line_segment(parent_curve, model)

        # do it before later update which needs self._model_list.
        self._model_list.append(model)

        # update anchors offset
        updater = InfinityCurveUpdater(self._model_list)
        updater.update_linear_pre_model(parent_curve)

    def build_linear_post_model(self, parent_curve):
        model = InfinityCurveModel()
        self._build_line_segment(parent_curve, model)

        # do it before later update which needs self._model_list.
        self._model_list.append(model)

        # update anchors offset
        updater = InfinityCurveUpdater(self._model_list)
        updater.update_linear_post_model(parent_curve)

    # build 2 anchor and 1 line segment in between. the anchor offset is default 0.
    def _build_line_segment(self, parent_curve, model):
        anchor0 = CurveInvisibleRect(parent_curve)
        anchor1 = CurveInvisibleRect(parent_curve)
        anchor0.build_ui(0, 0)
        anchor1.build_ui(0, 0)
        model._anchor_rects.append(anchor0)
        model._anchor_rects.append(anchor1)

        s = CurveSegment(parent_curve)
        s.build_ui(anchor0, anchor1, None, 0, 0, 0, 0)
        model._segment_list.append(s)

    def _build_common_step(self, origin_control_segment: CurveControlSegment, anchor_rects, step_rects):
        # create step rect before segment creation
        step = CurveInvisibleRect(origin_control_segment._curve_wp())
        index = len(step_rects)  # to get anchor and next anchor.
        offset_x = anchor_rects[index + 1].get_ui_x()
        offset_y = anchor_rects[index].get_ui_y()
        step.build_ui(offset_x, offset_y)

        step_rects.append(step)

    def _build_mirror_anchor(self, origin_key_rect: CurveKeyRect, ui_offset_x_aggregated, anchor_rects):
        anchor = CurveInvisibleRect(origin_key_rect._curve_wp())
        offset_x = ui_offset_x_aggregated - origin_key_rect.get_key_ui_x()
        offset_y = origin_key_rect.get_key_ui_y()
        anchor.build_ui(offset_x, offset_y)
        anchor_rects.append(anchor)

    def _build_mirror_segment(
        self, origin_control_segment: CurveControlSegment, anchor_rects, step_rects, segment_list
    ):
        self._build_common_step(origin_control_segment, anchor_rects, step_rects)

        # create segment with step
        s = CurveSegment(origin_control_segment._curve_wp())
        start_tangent_width, start_tangent_height, end_tangent_width, end_tangent_height = get_ui_bezier_tangent(
            origin_control_segment._ui_bezier_segment
        )

        # width is negated
        index = len(segment_list)  # to get anchor and next anchor.
        s.build_ui(
            anchor_rects[index],
            anchor_rects[index + 1],
            step_rects[index],
            -float(start_tangent_width),
            start_tangent_height,
            -float(end_tangent_width),
            end_tangent_height,
        )
        s.show_as_bezier(origin_control_segment._ui_bezier_segment.visible)
        segment_list.append(s)

    def _build_anchor(self, origin_key_rect: CurveKeyRect, ui_offset_x_bias, ui_offset_y_bias, anchor_rects):
        anchor = CurveInvisibleRect(origin_key_rect._curve_wp())
        offset_x = origin_key_rect.get_key_ui_x() + ui_offset_x_bias
        offset_y = origin_key_rect.get_key_ui_y() + ui_offset_y_bias
        anchor.build_ui(offset_x, offset_y)
        anchor_rects.append(anchor)

    def _build_segment(self, origin_control_segment: CurveControlSegment, anchor_rects, step_rects, segment_list):
        self._build_common_step(origin_control_segment, anchor_rects, step_rects)

        # create segment with step
        s = CurveSegment(origin_control_segment._curve_wp())
        start_tangent_width, start_tangent_height, end_tangent_width, end_tangent_height = get_ui_bezier_tangent(
            origin_control_segment._ui_bezier_segment
        )
        index = len(segment_list)  # to get anchor and next anchor.
        s.build_ui(
            anchor_rects[index],
            anchor_rects[index + 1],
            step_rects[index],
            start_tangent_width,
            start_tangent_height,
            end_tangent_width,
            end_tangent_height,
        )
        s.show_as_bezier(origin_control_segment._ui_bezier_segment.visible)

        segment_list.append(s)


class InfinityCurve:
    def __init__(self):
        self._pre_model_list = []
        self._post_model_list = []
        self._pre_strategy = None
        self._post_strategy = None

    def update_ui(self, parent_curve):
        self._pre_strategy.update_ui_pre(parent_curve, self)
        self._post_strategy.update_ui_post(parent_curve, self)

    # conditionally build_ui_pre
    def adapt_ui_pre(self, parent_curve):
        if self._pre_strategy.adapt_ui_pre(parent_curve, self):
            self._build_ui_pre(parent_curve)

    # conditionally build_ui_post
    def adapt_ui_post(self, parent_curve):
        if self._post_strategy.adapt_ui_post(parent_curve, self):
            self._build_ui_post(parent_curve)

    def _build_ui_pre(self, parent_curve):
        with parent_curve._infinity_curve_pre_frame:
            with ui.ZStack():
                self._pre_strategy.build_ui_pre(parent_curve, self)

    def _build_ui_post(self, parent_curve):
        with parent_curve._infinity_curve_post_frame:
            with ui.ZStack():
                self._post_strategy.build_ui_post(parent_curve, self)

    # unconditionally build_ui_pre
    def rebuild_ui_pre(self, parent_curve, infinity_type):
        self._pre_strategy = create_infinity_type_strategy(infinity_type)
        self._pre_strategy.adapt_ui_pre(parent_curve, self)
        self._build_ui_pre(parent_curve)

    # unconditionally build_ui_post
    def rebuild_ui_post(self, parent_curve, infinity_type):
        self._post_strategy = create_infinity_type_strategy(infinity_type)
        self._post_strategy.adapt_ui_post(parent_curve, self)
        self._build_ui_post(parent_curve)

    def update_ui_by_origin_segment(self, parent_curve, index):
        self._pre_strategy.update_ui_pre_by_origin_segment(parent_curve, index, self)
        self._post_strategy.update_ui_post_by_origin_segment(parent_curve, index, self)

    def update_ui_by_origin_anchor_x(self, parent_curve, index_start, index_end):
        if index_start == 0 or index_end + 1 == len(parent_curve._key_rects):
            # the first key time is changed, the period is changed
            # or the last key time is changed, the period is changed.
            self._pre_strategy.update_ui_pre_by_period(parent_curve, self)
            self._post_strategy.update_ui_post_by_period(parent_curve, self)
        else:
            for index in range(index_start, index_end + 1):
                self._pre_strategy.update_ui_pre_by_origin_anchor_x(parent_curve, index, self)
                self._post_strategy.update_ui_post_by_origin_anchor_x(parent_curve, index, self)

    def update_ui_by_origin_anchor_y(self, parent_curve, index_start, index_end):
        for index in range(index_start, index_end + 1):
            self._pre_strategy.update_ui_pre_by_origin_anchor_y(parent_curve, index, self)
            self._post_strategy.update_ui_post_by_origin_anchor_y(parent_curve, index, self)

    def update_ui_by_origin_segment_visibility(self, parent_curve, index):
        self._pre_strategy.update_ui_pre_by_origin_segment_visibility(parent_curve, index, self)
        self._post_strategy.update_ui_post_by_origin_segment_visibility(parent_curve, index, self)


class InfinityStrategy:
    def __init__(self):
        self._pre_left_period = 0
        self._pre_right_period = 0
        self._post_left_period = 0
        self._post_right_period = 0

    # helper function for subclasses
    def _get_pre_model_index(self, offset_period):
        return self._pre_left_period - offset_period

    # helper function for subclasses
    def _get_post_model_index(self, offset_period):
        return offset_period - self._post_left_period

    # helper function
    def _conditional_set_pre_period(self, pre_left_period, pre_right_period) -> bool:
        if self._pre_left_period == pre_left_period and self._pre_right_period == pre_right_period:
            # do not need to rebuild
            return False
        else:
            # print(f"pre_left_period {self._pre_left_period} => {pre_left_period}, pre_right_period {self._pre_right_period} => {pre_right_period}")
            self._pre_left_period = pre_left_period
            self._pre_right_period = pre_right_period
            return True

    # helper function
    def _conditional_set_post_period(self, post_left_period, post_right_period) -> bool:
        if self._post_left_period == post_left_period and self._post_right_period == post_right_period:
            # do not need to rebuild
            return False
        else:
            # print(f"post_left_period {self._post_left_period} => {post_left_period}, post_right_period {self._post_right_period} => {post_right_period}")
            self._post_left_period = post_left_period
            self._post_right_period = post_right_period
            return True

    # a stub for class tree
    def adapt_ui_pre(self, parent_curve, context) -> bool:
        return self._conditional_set_pre_period(1, 0)

    # a stub for class tree
    def adapt_ui_post(self, parent_curve, context) -> bool:
        return self._conditional_set_post_period(1, 2)

    # a stub for class tree
    def build_ui_pre(self, parent_curve, context):
        pass

    # a stub for class tree
    def build_ui_post(self, parent_curve, context):
        pass

    # a stub for class tree
    def update_ui_pre(self, parent_curve, context):
        pass

    # a stub for class tree
    def update_ui_post(self, parent_curve, context):
        pass

    # a stub for class tree
    def update_ui_pre_by_period(self, parent_curve, context):
        # the period changes. Defaults to refresh all
        self.update_ui_pre(parent_curve, context)

    # a stub for class tree
    def update_ui_post_by_period(self, parent_curve, context):
        # the period changes. Defaults to refresh all
        self.update_ui_post(parent_curve, context)

    # a stub for class tree
    def update_ui_pre_by_origin_segment(self, parent_curve, index, context):
        pass

    # a stub for class tree
    def update_ui_post_by_origin_segment(self, parent_curve, index, context):
        pass

    # a stub for class tree
    def update_ui_pre_by_origin_anchor_x(self, parent_curve, index, context):
        pass

    # a stub for class tree
    def update_ui_post_by_origin_anchor_x(self, parent_curve, index, context):
        pass

    # a stub for class tree
    def update_ui_pre_by_origin_anchor_y(self, parent_curve, index, context):
        pass

    # a stub for class tree
    def update_ui_post_by_origin_anchor_y(self, parent_curve, index, context):
        pass

    # a stub for class tree
    def update_ui_pre_by_origin_segment_visibility(self, parent_curve, index, context):
        pass

    # a stub for class tree
    def update_ui_post_by_origin_segment_visibility(self, parent_curve, index, context):
        pass


# this is a class for derivation only.
class InfinityStrategyPeriod(InfinityStrategy):
    def adapt_ui_pre(self, parent_curve, context) -> bool:
        timeline_begin_time = get_timeline_begin_time(parent_curve)
        timeline_end_time = get_timeline_end_time(parent_curve)
        first_sample_time = get_first_sample_time(parent_curve)
        last_sample_time = get_last_sample_time(parent_curve)
        period_time = last_sample_time - first_sample_time
        if period_time > 0:
            pre_left_period = int(max(math.ceil((first_sample_time - timeline_begin_time) / period_time), 0))
            pre_right_period = int(max(math.floor((first_sample_time - timeline_end_time) / period_time), 0))
        else:
            # special case only one key.
            pre_left_period = 0
            pre_right_period = 0

        return self._conditional_set_pre_period(pre_left_period, pre_right_period)

    def adapt_ui_post(self, parent_curve, context) -> bool:
        timeline_begin_time = get_timeline_begin_time(parent_curve)
        timeline_end_time = get_timeline_end_time(parent_curve)
        first_sample_time = get_first_sample_time(parent_curve)
        last_sample_time = get_last_sample_time(parent_curve)
        period_time = last_sample_time - first_sample_time
        if period_time > 0:
            post_left_period = int(max(math.floor((timeline_begin_time - first_sample_time) / period_time), 1))
            post_right_period = int(max(math.ceil((timeline_end_time - first_sample_time) / period_time), 1))
        else:
            # special case only one key.
            post_left_period = 0
            post_right_period = 0

        return self._conditional_set_post_period(post_left_period, post_right_period)

    def update_ui_pre_by_origin_segment_visibility(self, parent_curve, index, context):
        updater = InfinityCurveSegmentUpdater(context._pre_model_list)
        if self._pre_left_period - self._pre_right_period != updater.get_model_quantity():
            carb.log_error(
                "Unexpected code path in InfinityStrategyPeriod.update_ui_pre_by_origin_segment_visibility()"
            )

        for offset_period in range(self._pre_left_period, self._pre_right_period, -1):
            updater.update_by_visibility(parent_curve, index, self._get_pre_model_index(offset_period))

    def update_ui_post_by_origin_segment_visibility(self, parent_curve, index, context):
        updater = InfinityCurveSegmentUpdater(context._post_model_list)
        if self._post_right_period - self._post_left_period != updater.get_model_quantity():
            carb.log_error(
                "Unexpected code path in InfinityStrategyPeriod.update_ui_post_by_origin_segment_visibility()"
            )

        for offset_period in range(self._post_left_period, self._post_right_period):
            updater.update_by_visibility(parent_curve, index, self._get_post_model_index(offset_period))


class InfinityStrategyConstant(InfinityStrategy):
    def build_ui_pre(self, parent_curve, context):
        builder = InfinityCurveBuilder()
        builder.build_constant_pre_model(parent_curve)

        context._pre_model_list = builder.get_model_list()

    def build_ui_post(self, parent_curve, context):
        builder = InfinityCurveBuilder()
        builder.build_constant_post_model(parent_curve)

        context._post_model_list = builder.get_model_list()

    def update_ui_pre(self, parent_curve, context):
        updater = InfinityCurveUpdater(context._pre_model_list)
        if self._pre_left_period != 1 or self._pre_right_period != 0:
            carb.log_error("Unexpected code path in InfinityStrategyConstant.update_ui_pre()")

        updater.update_constant_pre_model(parent_curve)

    def update_ui_post(self, parent_curve, context):
        updater = InfinityCurveUpdater(context._post_model_list)
        if self._post_left_period != 1 or self._post_right_period != 2:
            carb.log_error("Unexpected code path in InfinityStrategyConstant.update_ui_post()")

        updater.update_constant_post_model(parent_curve)

    # x and y change use the same code path
    def _update_ui_pre_by_origin_anchor(self, parent_curve, index, context):
        if index == 0:
            # only the first key change, may trigger pre line change.
            self.update_ui_pre(parent_curve, context)

    # x and y change use the same code path
    def _update_ui_post_by_origin_anchor(self, parent_curve, index, context):
        if index == parent_curve._get_key_quantity() - 1:
            # only the last key change, may trigger post line change.
            self.update_ui_post(parent_curve, context)

    def update_ui_pre_by_origin_anchor_x(self, parent_curve, index, context):
        self._update_ui_pre_by_origin_anchor(parent_curve, index, context)

    def update_ui_post_by_origin_anchor_x(self, parent_curve, index, context):
        self._update_ui_post_by_origin_anchor(parent_curve, index, context)

    def update_ui_pre_by_origin_anchor_y(self, parent_curve, index, context):
        self._update_ui_pre_by_origin_anchor(parent_curve, index, context)

    def update_ui_post_by_origin_anchor_y(self, parent_curve, index, context):
        self._update_ui_post_by_origin_anchor(parent_curve, index, context)


class InfinityStrategyCycle(InfinityStrategyPeriod):
    def build_ui_pre(self, parent_curve, context):
        builder = InfinityCurveBuilder()

        period_x = get_period_ui_x(parent_curve)
        for offset_period in range(self._pre_left_period, self._pre_right_period, -1):
            builder.build_model(parent_curve, -offset_period * period_x, 0)

        context._pre_model_list = builder.get_model_list()

    def build_ui_post(self, parent_curve, context):
        builder = InfinityCurveBuilder()

        period_x = get_period_ui_x(parent_curve)
        for offset_period in range(self._post_left_period, self._post_right_period):
            builder.build_model(parent_curve, offset_period * period_x, 0)

        context._post_model_list = builder.get_model_list()

    def update_ui_pre(self, parent_curve, context):
        updater = InfinityCurveUpdater(context._pre_model_list)
        if self._pre_left_period - self._pre_right_period != updater.get_model_quantity():
            carb.log_error("Unexpected code path in InfinityStratedyCycle.update_ui_pre()")

        period_x = get_period_ui_x(parent_curve)
        for offset_period in range(self._pre_left_period, self._pre_right_period, -1):
            updater.update_model(parent_curve, self._get_pre_model_index(offset_period), -period_x * offset_period, 0)

    def update_ui_post(self, parent_curve, context):
        updater = InfinityCurveUpdater(context._post_model_list)
        if self._post_right_period - self._post_left_period != updater.get_model_quantity():
            carb.log_error("Unexpected code path in InfinityStratedyCycle.update_ui_post()")

        period_x = get_period_ui_x(parent_curve)
        for offset_period in range(self._post_left_period, self._post_right_period):
            updater.update_model(parent_curve, self._get_post_model_index(offset_period), period_x * offset_period, 0)

    def update_ui_pre_by_origin_segment(self, parent_curve, index, context):
        updater = InfinityCurveSegmentUpdater(context._pre_model_list)
        if self._pre_left_period - self._pre_right_period != updater.get_model_quantity():
            carb.log_error("Unexpected code path in InfinityStratedyCycle.update_ui_pre_by_origin_segment()")

        for offset_period in range(self._pre_left_period, self._pre_right_period, -1):
            updater.update_model(parent_curve, index, self._get_pre_model_index(offset_period))

    def update_ui_post_by_origin_segment(self, parent_curve, index, context):
        updater = InfinityCurveSegmentUpdater(context._post_model_list)
        if self._post_right_period - self._post_left_period != updater.get_model_quantity():
            carb.log_error("Unexpected code path in InfinityStratedyCycle.update_ui_post_by_origin_segment()")

        for offset_period in range(self._post_left_period, self._post_right_period):
            updater.update_model(parent_curve, index, self._get_post_model_index(offset_period))

    def update_ui_pre_by_origin_anchor_x(self, parent_curve, index, context):
        updater = InfinityCurveAnchorUpdater(context._pre_model_list)
        if self._pre_left_period - self._pre_right_period != updater.get_model_quantity():
            carb.log_error("Unexpected code path in InfinityStratedyCycle.update_ui_pre_by_origin_anchor_x()")

        period_x = get_period_ui_x(parent_curve)
        for offset_period in range(self._pre_left_period, self._pre_right_period, -1):
            updater.update_model_x(
                parent_curve, index, self._get_pre_model_index(offset_period), -period_x * offset_period
            )

    def update_ui_post_by_origin_anchor_x(self, parent_curve, index, context):
        updater = InfinityCurveAnchorUpdater(context._post_model_list)
        if self._post_right_period - self._post_left_period != updater.get_model_quantity():
            carb.log_error("Unexpected code path in InfinityStratedyCycle.update_ui_post_by_origin_anchor_x()")

        period_x = get_period_ui_x(parent_curve)
        for offset_period in range(self._post_left_period, self._post_right_period):
            updater.update_model_x(
                parent_curve, index, self._get_post_model_index(offset_period), period_x * offset_period
            )

    def update_ui_pre_by_origin_anchor_y(self, parent_curve, index, context):
        updater = InfinityCurveAnchorUpdater(context._pre_model_list)
        if self._pre_left_period - self._pre_right_period != updater.get_model_quantity():
            carb.log_error("Unexpected code path in InfinityStratedyCycle.update_ui_pre_by_origin_anchor_y()")

        for offset_period in range(self._pre_left_period, self._pre_right_period, -1):
            updater.update_model_y(parent_curve, index, self._get_pre_model_index(offset_period), 0)

    def update_ui_post_by_origin_anchor_y(self, parent_curve, index, context):
        updater = InfinityCurveAnchorUpdater(context._post_model_list)
        if self._post_right_period - self._post_left_period != updater.get_model_quantity():
            carb.log_error("Unexpected code path in InfinityStratedyCycle.update_ui_post_by_origin_anchor_y()")

        for offset_period in range(self._post_left_period, self._post_right_period):
            updater.update_model_y(parent_curve, index, self._get_post_model_index(offset_period), 0)


class InfinityStrategyCycleRelative(InfinityStrategyPeriod):
    def build_ui_pre(self, parent_curve, context):
        builder = InfinityCurveBuilder()

        period_x = get_period_ui_x(parent_curve)
        period_y = get_period_ui_y(parent_curve)
        for offset_period in range(self._pre_left_period, self._pre_right_period, -1):
            builder.build_model(parent_curve, -offset_period * period_x, -offset_period * period_y)

        context._pre_model_list = builder.get_model_list()

    def build_ui_post(self, parent_curve, context):
        builder = InfinityCurveBuilder()

        period_x = get_period_ui_x(parent_curve)
        period_y = get_period_ui_y(parent_curve)
        for offset_period in range(self._post_left_period, self._post_right_period):
            builder.build_model(parent_curve, offset_period * period_x, offset_period * period_y)

        context._post_model_list = builder.get_model_list()

    def update_ui_pre(self, parent_curve, context):
        updater = InfinityCurveUpdater(context._pre_model_list)
        if self._pre_left_period - self._pre_right_period != updater.get_model_quantity():
            carb.log_error("Unexpected code path in InfinityStrategyCycleRelative.update_ui_pre()")

        period_x = get_period_ui_x(parent_curve)
        period_y = get_period_ui_y(parent_curve)
        for offset_period in range(self._pre_left_period, self._pre_right_period, -1):
            updater.update_model(
                parent_curve,
                self._get_pre_model_index(offset_period),
                -period_x * offset_period,
                -period_y * offset_period,
            )

    def update_ui_post(self, parent_curve, context):
        updater = InfinityCurveUpdater(context._post_model_list)
        if self._post_right_period - self._post_left_period != updater.get_model_quantity():
            carb.log_error("Unexpected code path in InfinityStrategyCycleRelative.update_ui_post()")

        period_x = get_period_ui_x(parent_curve)
        period_y = get_period_ui_y(parent_curve)
        for offset_period in range(self._post_left_period, self._post_right_period):
            updater.update_model(
                parent_curve,
                self._get_post_model_index(offset_period),
                period_x * offset_period,
                period_y * offset_period,
            )

    def update_ui_pre_by_origin_segment(self, parent_curve, index, context):
        updater = InfinityCurveSegmentUpdater(context._pre_model_list)
        if self._pre_left_period - self._pre_right_period != updater.get_model_quantity():
            carb.log_error("Unexpected code path in InfinityStrategyCycleRelative.update_ui_pre_by_origin_segment()")

        for offset_period in range(self._pre_left_period, self._pre_right_period, -1):
            updater.update_model(parent_curve, index, self._get_pre_model_index(offset_period))

    def update_ui_post_by_origin_segment(self, parent_curve, index, context):
        updater = InfinityCurveSegmentUpdater(context._post_model_list)
        if self._post_right_period - self._post_left_period != updater.get_model_quantity():
            carb.log_error("Unexpected code path in InfinityStrategyCycleRelative.update_ui_post_by_origin_segment()")

        for offset_period in range(self._post_left_period, self._post_right_period):
            updater.update_model(parent_curve, index, self._get_post_model_index(offset_period))

    def update_ui_pre_by_origin_anchor_x(self, parent_curve, index, context):
        updater = InfinityCurveAnchorUpdater(context._pre_model_list)
        if self._pre_left_period - self._pre_right_period != updater.get_model_quantity():
            carb.log_error("Unexpected code path in InfinityStrategyCycleRelative.update_ui_pre_by_origin_anchor_x()")

        period_x = get_period_ui_x(parent_curve)
        for offset_period in range(self._pre_left_period, self._pre_right_period, -1):
            updater.update_model_x(
                parent_curve, index, self._get_pre_model_index(offset_period), -period_x * offset_period
            )

    def update_ui_post_by_origin_anchor_x(self, parent_curve, index, context):
        updater = InfinityCurveAnchorUpdater(context._post_model_list)
        if self._post_right_period - self._post_left_period != updater.get_model_quantity():
            carb.log_error("Unexpected code path in InfinityStrategyCycleRelative.update_ui_post_by_origin_anchor_x()")

        period_x = get_period_ui_x(parent_curve)
        for offset_period in range(self._post_left_period, self._post_right_period):
            updater.update_model_x(
                parent_curve, index, self._get_post_model_index(offset_period), period_x * offset_period
            )

    def update_ui_pre_by_origin_anchor_y(self, parent_curve, index, context):
        updater = InfinityCurveAnchorUpdater(context._pre_model_list)
        if self._pre_left_period - self._pre_right_period != updater.get_model_quantity():
            carb.log_error("Unexpected code path in InfinityStrategyCycleRelative.update_ui_pre_by_origin_anchor_y()")

        period_y = get_period_ui_y(parent_curve)
        for offset_period in range(self._pre_left_period, self._pre_right_period, -1):
            updater.update_model_y(
                parent_curve, index, self._get_pre_model_index(offset_period), -period_y * offset_period
            )

    def update_ui_post_by_origin_anchor_y(self, parent_curve, index, context):
        updater = InfinityCurveAnchorUpdater(context._post_model_list)
        if self._post_right_period - self._post_left_period != updater.get_model_quantity():
            carb.log_error("Unexpected code path in InfinityStrategyCycleRelative.update_ui_post_by_origin_anchor_y()")

        period_y = get_period_ui_y(parent_curve)
        for offset_period in range(self._post_left_period, self._post_right_period):
            updater.update_model_y(
                parent_curve, index, self._get_post_model_index(offset_period), period_y * offset_period
            )


class InfinityStrategyLinear(InfinityStrategy):
    def build_ui_pre(self, parent_curve, context):
        builder = InfinityCurveBuilder()
        builder.build_linear_pre_model(parent_curve)

        context._pre_model_list = builder.get_model_list()

    def build_ui_post(self, parent_curve, context):
        builder = InfinityCurveBuilder()
        builder.build_linear_post_model(parent_curve)

        context._post_model_list = builder.get_model_list()

    def update_ui_pre(self, parent_curve, context):
        updater = InfinityCurveUpdater(context._pre_model_list)
        if self._pre_left_period != 1 or self._pre_right_period != 0:
            carb.log_error("Unexpected code path in InfinityStrategyLinear.update_ui_pre()")

        updater.update_linear_pre_model(parent_curve)

    def update_ui_post(self, parent_curve, context):
        updater = InfinityCurveUpdater(context._post_model_list)
        if self._post_left_period != 1 or self._post_right_period != 2:
            carb.log_error("Unexpected code path in InfinityStrategyLinear.update_ui_post()")

        updater.update_linear_post_model(parent_curve)

    def update_ui_pre_by_origin_segment(self, parent_curve, index, context):
        if index == 0:
            # only the first segment change, might trigger pre line change.
            self.update_ui_pre(parent_curve, context)

    def update_ui_post_by_origin_segment(self, parent_curve, index, context):
        if index == parent_curve._get_segment_quantity() - 1:
            # only the last segment change, might trigger post line change.
            self.update_ui_post(parent_curve, context)

    # x and y change use the same code path
    def _update_ui_pre_by_origin_anchor(self, parent_curve, index, context):
        if index == 0:
            # only the first key change, may trigger pre line change.
            self.update_ui_pre(parent_curve, context)

    # x and y change use the same code path
    def _update_ui_post_by_origin_anchor(self, parent_curve, index, context):
        if index == parent_curve._get_key_quantity() - 1:
            # only the last key change, may trigger post line change.
            self.update_ui_post(parent_curve, context)

    def update_ui_pre_by_origin_anchor_x(self, parent_curve, index, context):
        self._update_ui_pre_by_origin_anchor(parent_curve, index, context)

    def update_ui_post_by_origin_anchor_x(self, parent_curve, index, context):
        self._update_ui_post_by_origin_anchor(parent_curve, index, context)

    def update_ui_pre_by_origin_anchor_y(self, parent_curve, index, context):
        self._update_ui_pre_by_origin_anchor(parent_curve, index, context)

    def update_ui_post_by_origin_anchor_y(self, parent_curve, index, context):
        self._update_ui_post_by_origin_anchor(parent_curve, index, context)


class InfinityStrategyOscillate(InfinityStrategyPeriod):
    def _is_mirror_model(self, offset_period) -> bool:
        return int(offset_period / 2) * 2 != offset_period

    def build_ui_pre(self, parent_curve, context):
        builder = InfinityCurveBuilder()

        period_x = get_period_ui_x(parent_curve)
        double_middle_x = get_double_middle_ui_x(parent_curve)
        for offset_period in range(self._pre_left_period, self._pre_right_period, -1):
            if self._is_mirror_model(offset_period):
                builder.build_mirror_model(parent_curve, double_middle_x - offset_period * period_x)
            else:
                builder.build_model(parent_curve, -offset_period * period_x, 0)

        context._pre_model_list = builder.get_model_list()

    def build_ui_post(self, parent_curve, context):
        builder = InfinityCurveBuilder()

        period_x = get_period_ui_x(parent_curve)
        double_middle_x = get_double_middle_ui_x(parent_curve)
        for offset_period in range(self._post_left_period, self._post_right_period):
            if self._is_mirror_model(offset_period):
                builder.build_mirror_model(parent_curve, double_middle_x + offset_period * period_x)
            else:
                builder.build_model(parent_curve, offset_period * period_x, 0)

        context._post_model_list = builder.get_model_list()

    def update_ui_pre(self, parent_curve, context):
        updater = InfinityCurveUpdater(context._pre_model_list)
        if self._pre_left_period - self._pre_right_period != updater.get_model_quantity():
            carb.log_error("Unexpected code path in InfinityStrategyOscillate.update_ui_pre()")

        period_x = get_period_ui_x(parent_curve)
        double_middle_x = get_double_middle_ui_x(parent_curve)
        for offset_period in range(self._pre_left_period, self._pre_right_period, -1):
            if self._is_mirror_model(offset_period):
                updater.update_mirror_model(
                    parent_curve, self._get_pre_model_index(offset_period), double_middle_x - period_x * offset_period
                )
            else:
                updater.update_model(
                    parent_curve, self._get_pre_model_index(offset_period), -period_x * offset_period, 0
                )

    def update_ui_post(self, parent_curve, context):
        updater = InfinityCurveUpdater(context._post_model_list)
        if self._post_right_period - self._post_left_period != updater.get_model_quantity():
            carb.log_error("Unexpected code path in InfinityStrategyOscillate.update_ui_post()")

        period_x = get_period_ui_x(parent_curve)
        double_middle_x = get_double_middle_ui_x(parent_curve)
        for offset_period in range(self._post_left_period, self._post_right_period):
            if self._is_mirror_model(offset_period):
                updater.update_mirror_model(
                    parent_curve, self._get_post_model_index(offset_period), double_middle_x + period_x * offset_period
                )
            else:
                updater.update_model(
                    parent_curve, self._get_post_model_index(offset_period), period_x * offset_period, 0
                )

    def update_ui_pre_by_origin_segment(self, parent_curve, index, context):
        updater = InfinityCurveSegmentUpdater(context._pre_model_list)
        if self._pre_left_period - self._pre_right_period != updater.get_model_quantity():
            carb.log_error("Unexpected code path in InfinityStrategyOscillate.update_ui_pre_by_origin_segment()")

        for offset_period in range(self._pre_left_period, self._pre_right_period, -1):
            if self._is_mirror_model(offset_period):
                updater.update_mirror_model(parent_curve, index, self._get_pre_model_index(offset_period))
            else:
                updater.update_model(parent_curve, index, self._get_pre_model_index(offset_period))

    def update_ui_post_by_origin_segment(self, parent_curve, index, context):
        updater = InfinityCurveSegmentUpdater(context._post_model_list)
        if self._post_right_period - self._post_left_period != updater.get_model_quantity():
            carb.log_error("Unexpected code path in InfinityStrategyOscillate.update_ui_post_by_origin_segment()")

        for offset_period in range(self._post_left_period, self._post_right_period):
            if self._is_mirror_model(offset_period):
                updater.update_mirror_model(parent_curve, index, self._get_post_model_index(offset_period))
            else:
                updater.update_model(parent_curve, index, self._get_post_model_index(offset_period))

    def update_ui_pre_by_origin_anchor_x(self, parent_curve, index, context):
        updater = InfinityCurveAnchorUpdater(context._pre_model_list)
        if self._pre_left_period - self._pre_right_period != updater.get_model_quantity():
            carb.log_error("Unexpected code path in InfinityStrategyOscillate.update_ui_pre_by_origin_anchor_x()")

        period_x = get_period_ui_x(parent_curve)
        double_middle_x = get_double_middle_ui_x(parent_curve)
        for offset_period in range(self._pre_left_period, self._pre_right_period, -1):
            if self._is_mirror_model(offset_period):
                updater.update_mirror_model_x(
                    parent_curve,
                    index,
                    self._get_pre_model_index(offset_period),
                    double_middle_x - period_x * offset_period,
                )
            else:
                updater.update_model_x(
                    parent_curve, index, self._get_pre_model_index(offset_period), -period_x * offset_period
                )

    def update_ui_post_by_origin_anchor_x(self, parent_curve, index, context):
        updater = InfinityCurveAnchorUpdater(context._post_model_list)
        if self._post_right_period - self._post_left_period != updater.get_model_quantity():
            carb.log_error("Unexpected code path in InfinityStrategyOscillate.update_ui_post_by_origin_anchor_x()")

        period_x = get_period_ui_x(parent_curve)
        double_middle_x = get_double_middle_ui_x(parent_curve)
        for offset_period in range(self._post_left_period, self._post_right_period):
            if self._is_mirror_model(offset_period):
                updater.update_mirror_model_x(
                    parent_curve,
                    index,
                    self._get_post_model_index(offset_period),
                    double_middle_x + period_x * offset_period,
                )
            else:
                updater.update_model_x(
                    parent_curve, index, self._get_post_model_index(offset_period), period_x * offset_period
                )

    def update_ui_pre_by_origin_anchor_y(self, parent_curve, index, context):
        updater = InfinityCurveAnchorUpdater(context._pre_model_list)
        if self._pre_left_period - self._pre_right_period != updater.get_model_quantity():
            carb.log_error("Unexpected code path in InfinityStrategyOscillate.update_ui_pre_by_origin_anchor_y()")

        period_y = get_period_ui_y(parent_curve)
        for offset_period in range(self._pre_left_period, self._pre_right_period, -1):
            if self._is_mirror_model(offset_period):
                updater.update_mirror_model_y(parent_curve, index, self._get_pre_model_index(offset_period))
            else:
                updater.update_model_y(parent_curve, index, self._get_pre_model_index(offset_period), 0)

    def update_ui_post_by_origin_anchor_y(self, parent_curve, index, context):
        updater = InfinityCurveAnchorUpdater(context._post_model_list)
        if self._post_right_period - self._post_left_period != updater.get_model_quantity():
            carb.log_error("Unexpected code path in InfinityStrategyOscillate.update_ui_post_by_origin_anchor_y()")

        period_y = get_period_ui_y(parent_curve)
        for offset_period in range(self._post_left_period, self._post_right_period):
            if self._is_mirror_model(offset_period):
                updater.update_mirror_model_y(parent_curve, index, self._get_post_model_index(offset_period))
            else:
                updater.update_model_y(parent_curve, index, self._get_post_model_index(offset_period), 0)


def create_infinity_type_strategy(infinity_type):
    if infinity_type == CurveInfinityTypes.InfinityType.Constant:
        strategy = InfinityStrategyConstant()
    elif infinity_type == CurveInfinityTypes.InfinityType.Cycle:
        strategy = InfinityStrategyCycle()
    elif infinity_type == CurveInfinityTypes.InfinityType.CycleRelative:
        strategy = InfinityStrategyCycleRelative()
    elif infinity_type == CurveInfinityTypes.InfinityType.Linear:
        strategy = InfinityStrategyLinear()
    elif infinity_type == CurveInfinityTypes.InfinityType.Oscillate:
        strategy = InfinityStrategyOscillate()
    else:
        strategy = None

    return strategy


def get_first_sample_time(parent_curve):
    return parent_curve._get_time_code_from_index(0)


def get_last_sample_time(parent_curve):
    return parent_curve._get_time_code_from_index(-1)


def get_timeline_begin_time(parent_curve):
    return parent_curve.get_curve_editor_timeline()._timeline_begin


def get_timeline_end_time(parent_curve):
    return parent_curve.get_curve_editor_timeline()._timeline_end


def get_origin_tangent(parent_curve, index):  # pragma: no cover    Unused code
    origin_ui_bezier_segment = parent_curve._segment_list[index]._ui_bezier_segment
    start_tangent_width, start_tangent_height, end_tangent_width, end_tangent_height = get_ui_bezier_tangent(
        origin_ui_bezier_segment
    )
    return start_tangent_width, start_tangent_height, end_tangent_width, end_tangent_height


def get_ui_bezier_tangent(origin_ui_bezier_segment):
    start_tangent_width = origin_ui_bezier_segment.start_tangent_width
    start_tangent_height = origin_ui_bezier_segment.start_tangent_height
    end_tangent_width = origin_ui_bezier_segment.end_tangent_width
    end_tangent_height = origin_ui_bezier_segment.end_tangent_height
    return start_tangent_width, start_tangent_height, end_tangent_width, end_tangent_height


def get_double_middle_ui_x(parent_curve):
    first_sample_offset_x = parent_curve._key_rects[0].get_key_ui_x()
    last_sample_offset_x = parent_curve._key_rects[-1].get_key_ui_x()
    return last_sample_offset_x + first_sample_offset_x


def get_period_ui_x(parent_curve):
    first_sample_offset_x = parent_curve._key_rects[0].get_key_ui_x()
    last_sample_offset_x = parent_curve._key_rects[-1].get_key_ui_x()
    return last_sample_offset_x - first_sample_offset_x


def get_period_ui_y(parent_curve):
    first_sample_offset_y = parent_curve._key_rects[0].get_key_ui_y()
    last_sample_offset_y = parent_curve._key_rects[-1].get_key_ui_y()
    return last_sample_offset_y - first_sample_offset_y
