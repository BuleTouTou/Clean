<script setup lang="ts">
import { computed, h, ref } from "vue";
import { useQuery } from "@tanstack/vue-query";
import {
  NButton,
  NCard,
  NDataTable,
  NEmpty,
  NInput,
  NPagination,
  NSelect,
  NSpace,
  NSpin,
  NTag,
  useMessage,
} from "naive-ui";
import { api, type BatchKind, type ReportItem } from "../../api";

const message = useMessage();
const search = ref("");
const reportPage = ref(1);
const reportKind = ref<BatchKind | undefined>();

const reportQuery = useQuery({
  queryKey: computed(() => ["reports", reportPage.value, reportKind.value]),
  queryFn: () => api.reports(reportPage.value, 20, reportKind.value),
});

const filteredReports = computed(() => {
  const items = reportQuery.data.value?.items ?? [];
  const keyword = search.value.trim().toLowerCase();
  if (!keyword) return items;
  return items.filter((item: ReportItem) =>
    item.original_name.toLowerCase().includes(keyword) || item.task_id.toLowerCase().includes(keyword),
  );
});

function downloadUrl(row: ReportItem) {
  return row.output_file ? `/download/${row.output_file.split(/[\\/]/).map(encodeURIComponent).join("/")}` : "";
}

function openReport(row: ReportItem) {
  if (row.output_file) window.open(downloadUrl(row), "_blank");
  else message.info("该报告没有可下载的文件");
}

const reportColumns = [
  {
    title: "任务",
    key: "task_id",
    render: (row: ReportItem) => h("div", [
      h("div", { class: "font-medium" }, row.task_id),
      h("div", { class: "text-xs text-slate-400" }, row.original_name),
    ]),
  },
  {
    title: "类型",
    key: "kind",
    render: (row: ReportItem) => h(
      NTag,
      { type: row.kind === "sale" ? "error" : "info", bordered: false },
      { default: () => (row.kind === "sale" ? "出售" : "出租") },
    ),
  },
  { title: "记录", key: "output_rows", render: (row: ReportItem) => `${row.output_rows} / ${row.input_rows}` },
  {
    title: "阻断异常",
    key: "blocking_count",
    render: (row: ReportItem) => h(
      NTag,
      { type: row.blocking_count ? "warning" : "success", bordered: false },
      { default: () => String(row.blocking_count) },
    ),
  },
  { title: "完成时间", key: "completed_at" },
  {
    title: "操作",
    key: "actions",
    render: (row: ReportItem) => h(
      NButton,
      { size: "small", tertiary: true, onClick: () => openReport(row) },
      { default: () => "查看报告" },
    ),
  },
];
</script>

<template>
  <div class="mb-8 flex flex-wrap items-end justify-between gap-4">
    <div>
      <div class="text-sm font-semibold uppercase tracking-widest text-[#b44236]">历史报告</div>
      <h1 class="mt-2 text-3xl font-bold text-slate-800">清洗任务记录</h1>
      <p class="mt-2 text-slate-500">所有已完成的导出任务都会在这里留下报告。</p>
    </div>
    <n-space>
      <n-input v-model:value="search" clearable placeholder="搜索任务或文件名" />
      <n-select
        v-model:value="reportKind"
        clearable
        class="w-32"
        placeholder="全部类型"
        :options="[{ label: '出售', value: 'sale' }, { label: '出租', value: 'rent' }]"
      />
    </n-space>
  </div>

  <n-card class="shadow-sm">
    <n-spin :show="reportQuery.isLoading.value">
      <n-data-table :columns="reportColumns" :data="filteredReports" :bordered="false" :single-line="false" />
      <n-empty v-if="!reportQuery.isLoading.value && !filteredReports.length" description="暂无历史报告" class="py-16" />
      <div class="mt-5 flex justify-end">
        <n-pagination v-model:page="reportPage" :page-size="20" :item-count="reportQuery.data.value?.total ?? 0" />
      </div>
    </n-spin>
  </n-card>
</template>
