<script setup lang="ts">
import { ref } from "vue";
import { useMutation, useQuery, useQueryClient } from "@tanstack/vue-query";
import {
  NAlert,
  NButton,
  NCard,
  NCollapse,
  NCollapseItem,
  NDatePicker,
  NRadio,
  NRadioGroup,
  NResult,
  NSelect,
  NSpace,
  NSpin,
  NTag,
  useMessage,
} from "naive-ui";
import {
  api,
  type BatchKind,
  type BuildingReviewItem,
  type EstateReviewBuilding,
  type EstateReviewCandidate,
  type EstateReviewGroup,
  type EstateSelectionMethod,
  type ExportResponse,
  type SheetInfo,
} from "../api";

const message = useMessage();
const queryClient = useQueryClient();
const kind = ref<BatchKind | null>(null);
const taskId = ref("");
const step = ref(1);
const busy = ref(false);
const file = ref<File | null>(null);
const sheets = ref<SheetInfo[]>([]);
const targets = ref<string[]>([]);
const suggestions = ref<Awaited<ReturnType<typeof api.selectSheet>>["suggestions"]>([]);
const mapping = ref<Record<string, string>>({});
const estateReviews = ref<EstateReviewGroup[]>([]);
const estateSelected = ref<Record<string, string>>({});
const estateSelectionMethods = ref<Record<string, EstateSelectionMethod>>({});
const buildingReviews = ref<BuildingReviewItem[]>([]);
const buildingSelected = ref<Record<string, string>>({});
const entrustDate = ref(Date.now());
const exportResult = ref<ExportResponse | null>(null);
const UNMATCHED_ESTATE = "__unmatched_estate__";

useQuery({
  queryKey: ["status"],
  queryFn: () => api.status(),
  staleTime: 30_000,
});

const createTaskMutation = useMutation({ mutationFn: (value: BatchKind) => api.createTask(value) });
const uploadMutation = useMutation({ mutationFn: ({ id, source }: { id: string; source: File }) => api.upload(id, source) });
const selectSheetMutation = useMutation({ mutationFn: ({ id, sheet }: { id: string; sheet: SheetInfo }) => api.selectSheet(id, sheet) });
const mappingMutation = useMutation({ mutationFn: ({ id, value }: { id: string; value: Record<string, string> }) => api.mapping(id, value) });
const buildingReviewMutation = useMutation({ mutationFn: ({ id, value, methods }: { id: string; value: Record<string, string>; methods: Record<string, EstateSelectionMethod> }) => api.buildingReview(id, value, methods) });
const buildingConfirmMutation = useMutation({ mutationFn: ({ id, value, date }: { id: string; value: Record<string, string>; date: string }) => api.buildingConfirm(id, value, date) });
const exportMutation = useMutation({ mutationFn: ({ id, cleanOnly }: { id: string; cleanOnly: boolean }) => api.export(id, cleanOnly) });

function resetTask() {
  taskId.value = "";
  step.value = 1;
  file.value = null;
  sheets.value = [];
  suggestions.value = [];
  mapping.value = {};
  estateReviews.value = [];
  estateSelected.value = {};
  estateSelectionMethods.value = {};
  buildingReviews.value = [];
  buildingSelected.value = {};
  exportResult.value = null;
}

function errorMessage(error: unknown): string {
  return error instanceof Error ? error.message : "操作失败，请稍后重试";
}

function handleFileChange(event: Event) {
  const input = event.target as HTMLInputElement;
  file.value = input.files?.[0] ?? null;
  upload();
}

async function createTask() {
  if (!kind.value) return;
  busy.value = true;
  try {
    const result = await createTaskMutation.mutateAsync(kind.value);
    taskId.value = result.taskId;
    step.value = 2;
    message.success("清洗任务已创建");
  } catch (error: unknown) {
    message.error(errorMessage(error));
  } finally {
    busy.value = false;
  }
}

async function upload() {
  if (!file.value || !taskId.value) return;
  busy.value = true;
  try {
    const result = await uploadMutation.mutateAsync({ id: taskId.value, source: file.value });
    sheets.value = result.sheets;
    message.success("文件识别完成");
  } catch (error: unknown) {
    message.error(errorMessage(error));
  } finally {
    busy.value = false;
  }
}

async function selectSheet(sheet: SheetInfo) {
  busy.value = true;
  try {
    const result = await selectSheetMutation.mutateAsync({ id: taskId.value, sheet });
    targets.value = result.targets;
    suggestions.value = result.suggestions;
    mapping.value = Object.fromEntries(result.suggestions.map((item) => [item.source, item.target || "__ignore__"]));
    step.value = 3;
  } catch (error: unknown) {
    message.error(errorMessage(error));
  } finally {
    busy.value = false;
  }
}

async function confirmMapping() {
  busy.value = true;
  try {
    const result = await mappingMutation.mutateAsync({ id: taskId.value, value: mapping.value });
    estateReviews.value = result.reviews;
    estateSelected.value = {};
    estateSelectionMethods.value = {};
    step.value = 4;
    message.success(`已自动匹配 ${result.autoCount} 个小区`);
  } catch (error: unknown) {
    message.error(errorMessage(error));
  } finally {
    busy.value = false;
  }
}

function groupBuildingSummary(group: EstateReviewGroup): string {
  const names = group.buildings.map((item) => item.rawBuilding || "栋座为空");
  if (names.length <= 5) return names.join("、");
  return `${names.slice(0, 5).join("、")} +${names.length - 5}`;
}

function candidateOptions(group: EstateReviewGroup, building: EstateReviewBuilding) {
  return [
    { label: "暂不匹配", value: UNMATCHED_ESTATE },
    ...group.candidates
    .filter((candidate) => building.candidateIds.includes(candidate.id))
    .map((candidate) => ({
      label: `${candidate.outputName} · ${candidate.district} · ${candidate.businessArea}`,
      value: candidate.id,
    })),
  ];
}

function buildingCandidateState(candidate: EstateReviewCandidate, buildingKey: string): "unique" | "compatible" | "unknown" | "incompatible" {
  if (candidate.uniqueBuildingKeys.includes(buildingKey)) return "unique";
  if (candidate.compatibleBuildingKeys.includes(buildingKey)) return "compatible";
  if (candidate.unknownBuildingKeys.includes(buildingKey)) return "unknown";
  return "incompatible";
}

function selectedCandidate(group: EstateReviewGroup, building: EstateReviewBuilding): EstateReviewCandidate | undefined {
  return group.candidates.find((candidate) => candidate.id === estateSelected.value[building.key]);
}

function buildingStatus(group: EstateReviewGroup, building: EstateReviewBuilding): { label: string; type: "success" | "info" | "warning" | "error" | "default" } {
  if (estateSelected.value[building.key] === UNMATCHED_ESTATE) return { label: "暂不匹配", type: "default" };
  const candidate = selectedCandidate(group, building);
  if (!candidate) return { label: "待确认", type: "warning" };
  const method = estateSelectionMethods.value[building.key] || "manual";
  if (method === "batch-all") return { label: "批量完成", type: "success" };
  if (method === "batch-compatible") return { label: "兼容批量", type: "info" };
  const state = buildingCandidateState(candidate, building.key);
  return state === "incompatible"
    ? { label: "人工覆盖", type: "warning" }
    : { label: "人工完成", type: "success" };
}

function updateEstateSelection(key: string, value: string | null) {
  if (value === null) {
    delete estateSelected.value[key];
    delete estateSelectionMethods.value[key];
    return;
  }
  estateSelected.value[key] = value;
  if (value === UNMATCHED_ESTATE) delete estateSelectionMethods.value[key];
  else estateSelectionMethods.value[key] = "manual";
}

function applyEstateCandidate(group: EstateReviewGroup, candidate: EstateReviewCandidate) {
  const keys = candidate.canApplyAll
    ? group.buildings.map((item) => item.key)
    : candidate.compatibleBuildingKeys;
  const method: EstateSelectionMethod = candidate.canApplyAll ? "batch-all" : "batch-compatible";
  for (const key of keys) {
    estateSelected.value[key] = candidate.id;
    estateSelectionMethods.value[key] = method;
  }
  message.success(
    candidate.canApplyAll
      ? `已为 ${keys.length} 个栋座一键匹配 ${candidate.outputName}`
      : `已匹配 ${keys.length} 个兼容栋座，冲突项仍需人工确认`,
  );
}

function markEstateGroupUnmatched(group: EstateReviewGroup) {
  for (const building of group.buildings) {
    estateSelected.value[building.key] = UNMATCHED_ESTATE;
    delete estateSelectionMethods.value[building.key];
  }
  message.info(`已将 ${group.raw || "该小区"} 的 ${group.buildings.length} 个栋座设为暂不匹配`);
}

function unresolvedBuildings(): number {
  return estateReviews.value.reduce(
    (total, group) => total + group.buildings.filter((item) => !estateSelected.value[item.key]).length,
    0,
  );
}

async function confirmEstate() {
  busy.value = true;
  try {
    const selected = Object.fromEntries(
      Object.entries(estateSelected.value).map(([key, value]) => [key, value === UNMATCHED_ESTATE ? "" : value]),
    );
    const result = await buildingReviewMutation.mutateAsync({ id: taskId.value, value: selected, methods: estateSelectionMethods.value });
    buildingReviews.value = result.reviews;
    buildingSelected.value = {};
    step.value = 5;
  } catch (error: unknown) {
    message.error(errorMessage(error));
  } finally {
    busy.value = false;
  }
}

async function confirmBuilding() {
  busy.value = true;
  try {
    await buildingConfirmMutation.mutateAsync({
      id: taskId.value,
      value: buildingSelected.value,
      date: new Date(entrustDate.value).toISOString().slice(0, 10),
    });
    step.value = 6;
  } catch (error: unknown) {
    message.error(errorMessage(error));
  } finally {
    busy.value = false;
  }
}

async function exportFile(cleanOnly: boolean) {
  busy.value = true;
  try {
    exportResult.value = await exportMutation.mutateAsync({ id: taskId.value, cleanOnly });
    message.success("文件已生成");
    await queryClient.invalidateQueries({ queryKey: ["reports"] });
  } catch (error: unknown) {
    message.error(errorMessage(error));
  } finally {
    busy.value = false;
  }
}
</script>

<template>
  <div class="mb-8 flex items-center justify-between">
    <div>
      <div class="text-sm font-semibold uppercase tracking-widest text-tsinghua">任务执行</div>
      <h1 class="mt-2 text-3xl font-bold text-slate-800">房源数据清洗</h1>
      <p class="mt-2 text-slate-500">从原始文件到标准导入文件，逐步确认每一个关键结果。</p>
    </div>
    <n-tag v-if="taskId" type="info" round>任务 {{ taskId }}</n-tag>
  </div>

  <n-spin :show="busy">
    <n-card v-if="step === 1" title="创建清洗批次" class="shadow-sm">
      <p class="mb-5 text-slate-500">请选择本次数据对应的业务类型。</p>
      <n-space>
        <n-button :type="kind === 'sale' ? 'primary' : 'default'" size="large" @click="kind = 'sale'">出售房源</n-button>
        <n-button :type="kind === 'rent' ? 'primary' : 'default'" size="large" @click="kind = 'rent'">出租房源</n-button>
      </n-space>
      <div class="mt-6 flex justify-end"><n-button type="primary" :disabled="!kind" @click="createTask">创建任务并上传文件</n-button></div>
    </n-card>

    <n-card v-else-if="step === 2" title="上传原始文件" class="shadow-sm">
      <input type="file" accept=".csv,.xls,.xlsx" class="mb-5 block w-full rounded border border-dashed border-slate-300 bg-white p-8" @change="handleFileChange" />
      <n-alert v-if="sheets.length" type="success" title="文件识别完成" class="mb-4">请选择要清洗的工作表。</n-alert>
      <div v-for="sheet in sheets" :key="sheet.name" class="mb-3 flex items-center justify-between rounded-lg border bg-white p-4">
        <div>
          <div class="font-medium">{{ sheet.name }}</div>
          <div class="text-sm text-slate-500">{{ sheet.rows }} 条记录 · {{ sheet.cols }} 列 · 表头第 {{ sheet.headerRow }} 行</div>
        </div>
        <n-button type="primary" secondary @click="selectSheet(sheet)">选择工作表</n-button>
      </div>
    </n-card>

    <n-card v-else-if="step === 3" title="确认字段映射" class="shadow-sm">
      <div class="overflow-x-auto">
        <table class="w-full text-left text-sm">
          <thead><tr class="border-b text-slate-500"><th class="p-3">原始字段</th><th class="p-3">目标字段</th><th class="p-3">置信度</th><th class="p-3">判断依据</th></tr></thead>
          <tbody>
            <tr v-for="item in suggestions" :key="item.source" class="border-b">
              <td class="p-3 font-medium">{{ item.source }}</td>
              <td class="p-3"><n-select v-model:value="mapping[item.source]" :options="[{ label: '不导入', value: '__ignore__' }, ...targets.map((target) => ({ label: target, value: target }))]" /></td>
              <td class="p-3">{{ Math.round(item.confidence * 100) }}%</td>
              <td class="p-3 text-slate-500">{{ item.reason }}</td>
            </tr>
          </tbody>
        </table>
      </div>
      <div class="mt-6 flex justify-end">
        <n-button type="primary" @click="confirmMapping">确认映射 检查楼盘</n-button>
      </div>
    </n-card>

    <n-card v-else-if="step === 4" title="楼盘审核" class="shadow-sm">
      <n-alert class="mb-4" :type="estateReviews.length ? 'info' : 'success'">
        {{ estateReviews.length ? "同一原始小区已合并展示。系统只会对字典可验证的栋座执行批量匹配，冲突项仍需逐项确认。" : "小区与期名已全部自动确认，无需人工复核。" }}
      </n-alert>
      <n-collapse v-if="estateReviews.length" :default-expanded-names="estateReviews.map((group) => group.key)">
        <n-collapse-item v-for="group in estateReviews" :key="group.key" :name="group.key">
          <template #header>
            <div class="min-w-0 py-2">
              <div class="flex flex-wrap items-center gap-2">
                <span class="font-semibold text-slate-800">{{ group.raw || "小区名称为空" }}</span>
                <n-tag size="small" :bordered="false">影响 {{ group.rows.length }} 行</n-tag>
                <n-tag size="small" type="info" :bordered="false">{{ group.buildingCount }} 个栋座</n-tag>
                <n-tag v-if="group.buildings.some((item) => !estateSelected[item.key])" size="small" type="warning" :bordered="false">
                  待确认 {{ group.buildings.filter((item) => !estateSelected[item.key]).length }} 项
                </n-tag>
              </div>
              <div class="mt-1 truncate text-xs text-slate-500">栋座：{{ groupBuildingSummary(group) }}</div>
            </div>
          </template>

          <div class="mb-4 flex flex-wrap items-center justify-between gap-3 rounded-lg bg-amber-50 px-4 py-3">
            <span class="text-sm text-amber-800">无法确认标准楼盘时，可暂不匹配并在导出结果中保留阻断异常。</span>
            <n-button size="small" type="warning" secondary @click="markEstateGroupUnmatched(group)">全部暂不匹配</n-button>
          </div>

          <div class="mb-4 grid gap-3 xl:grid-cols-2">
            <div v-for="candidate in group.candidates" :key="candidate.id" class="rounded-lg border border-slate-200 bg-slate-50 p-4">
              <div class="flex flex-wrap items-start justify-between gap-3">
                <div>
                  <div class="font-semibold text-slate-800">{{ candidate.outputName }}</div>
                  <div class="mt-1 text-xs text-slate-500">{{ candidate.district }} · {{ candidate.businessArea }}</div>
                </div>
                <n-button
                  size="small"
                  :type="candidate.canApplyAll ? 'primary' : 'default'"
                  :disabled="!candidate.canApplyAll && !candidate.canApplyCompatible"
                  @click="applyEstateCandidate(group, candidate)"
                >
                  {{ candidate.canApplyAll ? "一键匹配全部" : candidate.canApplyCompatible ? "匹配兼容栋座" : "无可批量栋座" }}
                </n-button>
              </div>
              <div class="mt-3 flex flex-wrap gap-2 text-xs">
                <n-tag size="small" type="info" :bordered="false">覆盖 {{ candidate.coverageCount }}/{{ group.buildingCount }}</n-tag>
                <n-tag size="small" type="success" :bordered="false">唯一 {{ candidate.uniqueCoverageCount }}</n-tag>
                <n-tag v-if="candidate.conflictCount" size="small" type="warning" :bordered="false">冲突 {{ candidate.conflictCount }}</n-tag>
                <n-tag v-if="candidate.unknownBuildingKeys.length" size="small" :bordered="false">缺少期名依据 {{ candidate.unknownBuildingKeys.length }}</n-tag>
              </div>
            </div>
          </div>

          <div class="overflow-x-auto rounded-lg border border-slate-200">
            <table class="w-full min-w-[760px] text-left text-sm">
              <thead>
                <tr class="bg-slate-50 text-slate-500">
                  <th class="p-3">原始栋座</th>
                  <th class="p-3">影响行数</th>
                  <th class="p-3">标准小区与期名</th>
                  <th class="p-3">匹配状态</th>
                </tr>
              </thead>
              <tbody>
                <tr v-for="building in group.buildings" :key="building.key" class="border-t border-slate-100">
                  <td class="p-3 font-medium text-slate-800">{{ building.rawBuilding || "栋座为空" }}</td>
                  <td class="p-3 text-slate-500">{{ building.rows.length }} 行</td>
                  <td class="p-3">
                    <n-select
                      clearable
                      filterable
                      :value="estateSelected[building.key] || null"
                      :options="candidateOptions(group, building)"
                      placeholder="请选择标准小区"
                      @update:value="(value) => updateEstateSelection(building.key, value)"
                    />
                  </td>
                  <td class="p-3">
                    <n-tag :type="buildingStatus(group, building).type" :bordered="false">
                      {{ buildingStatus(group, building).label }}
                    </n-tag>
                  </td>
                </tr>
              </tbody>
            </table>
          </div>
        </n-collapse-item>
      </n-collapse>
      <div class="mt-6 flex flex-wrap items-center justify-end gap-3">
        <span v-if="unresolvedBuildings()" class="text-sm text-amber-700">仍有 {{ unresolvedBuildings() }} 个栋座未确认，可暂不匹配并在导出时保留阻断异常。</span>
        <n-button type="primary" @click="confirmEstate">保存确认并检查栋座</n-button>
      </div>
    </n-card>

    <n-card v-else-if="step === 5" title="栋座审核" class="shadow-sm">
      <n-alert class="mb-4">只有无法唯一确认的栋座需要选择。</n-alert>
      <div v-for="(review, index) in buildingReviews" :key="review.key || index" class="mb-4 rounded-lg border p-4">
        <div class="mb-3 font-medium">{{ review.estate }} · {{ review.raw }}</div>
        <n-radio-group v-model:value="buildingSelected[review.key]">
          <n-space vertical>
            <n-radio v-for="candidate in review.candidates" :key="candidate" :value="candidate">{{ candidate }}</n-radio>
            <n-radio value="">暂不匹配</n-radio>
          </n-space>
        </n-radio-group>
      </div>
      <div class="mb-5 max-w-xs">
        <div class="mb-2 text-sm text-slate-500">统一委托日期</div>
        <n-date-picker v-model:value="entrustDate" type="date" />
      </div>
      <div class="mt-6 flex justify-end">
        <n-button type="primary" @click="confirmBuilding">保存确认并进入导出</n-button>
      </div>
    </n-card>

    <n-card v-else title="导出结果" class="shadow-sm">
      <n-result v-if="!exportResult" status="info" title="清洗已完成" description="请选择导出方式" />
      <div v-else class="mb-5 rounded-lg bg-emerald-50 p-4 text-emerald-800">
        已生成 {{ exportResult.report?.最终输出记录数 }} 条记录，阻断异常 {{ exportResult.report?.阻断异常数量 }} 条。
      </div>
      <div class="flex justify-end">
        <n-space v-if="!exportResult">
          <n-button type="primary" @click="exportFile(false)">导出全部数据</n-button>
          <n-button secondary @click="exportFile(true)">仅导出无阻断异常</n-button>
        </n-space>
        <n-space v-else>
          <n-button type="primary" tag="a" :href="exportResult.downloadUrl || exportResult.ossUrl || '/download/' + exportResult.downloadId" target="_blank">下载文件</n-button>
          <n-button secondary @click="resetTask">开始新任务</n-button>
        </n-space>
      </div>
    </n-card>
  </n-spin>
</template>
