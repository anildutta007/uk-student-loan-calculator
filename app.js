/**
 * app.js - Client-Side Interactive Engine & Visualizer
 * UK UniLoan Calculator & Parental Contribution Lab (England & Wales)
 */

// Global State
let state = {
  mode: 'studying', // 'studying' or 'graduated'
  planType: 'plan_5',
  tuition: 9250,
  maintenance: 10227,
  courseYears: 3,
  gradBalance: 48000,
  salary: 32000,
  salaryGrowth: 0.035,
  rpi: 0.041,
  hasPostgrad: false,
  // Parental contribution
  contribType: 'annual_fee',
  parentAnnual: 9250,
  parentLump: 25000,
  customMarketRate: 0.06,
  horizon: 'write_off',
};

// Statutory Plan Configurations
const PLAN_CONFIGS = {
  plan_5: {
    name: 'Plan 5 (England: courses started on/after 1 August 2023)',
    threshold: 25000,
    monthlyThreshold: 2083,
    weeklyThreshold: 480,
    rate: 0.09,
    writeOffYears: 40,
    info: '£25,000 threshold (£2,083/mo), 9% repayment, 40-year write-off, flat RPI interest (currently 4.1%).'
  },
  plan_2: {
    name: 'Plan 2 (England: 1 Sept 2012 – 31 July 2023 | Wales: 1 Sept 2012 onwards)',
    threshold: 29385,
    monthlyThreshold: 2448,
    weeklyThreshold: 565,
    upperThreshold: 52884,
    rate: 0.09,
    writeOffYears: 30,
    info: '£29,385 threshold (£2,448/mo), 9% repayment, 30-year write-off, variable interest 4.1% to 6.0% (capped).'
  },
  plan_1: {
    name: 'Plan 1 (England & Wales: pre-1 Sept 2012 | Northern Ireland)',
    threshold: 26900,
    monthlyThreshold: 2241,
    weeklyThreshold: 517,
    rate: 0.09,
    writeOffYears: 25,
    info: '£26,900 threshold (£2,241/mo), 9% repayment, 25-year write-off, interest currently 4.1%.'
  }
};

const POSTGRAD_CONFIG = {
  threshold: 21000,
  monthlyThreshold: 1750,
  weeklyThreshold: 403,
  rate: 0.06,
  writeOffYears: 30,
  interestRate: 0.060
};

// Chart instances
let parentCompareChartInstance = null;
let studentTrajectoryChartInstance = null;

// Initialize on DOM load
document.addEventListener('DOMContentLoaded', () => {
  readInputsFromDOM();
  runCalculation();
});

// Google Analytics Event Tracking Helper
function trackGAEvent(eventName, eventParams = {}) {
  try {
    if (typeof window.gtag === 'function') {
      window.gtag('event', eventName, eventParams);
    }
  } catch (e) {
    // Ignore analytics errors silently
  }
}

// Tab Switching
function switchTab(tabId) {
  document.querySelectorAll('.tab-btn').forEach(btn => btn.classList.remove('active'));
  document.querySelectorAll('.tab-pane').forEach(pane => pane.classList.add('hidden'));

  const btn = document.getElementById(`tabBtn-${tabId}`);
  const pane = document.getElementById(`tabContent-${tabId}`);
  if (btn) btn.classList.add('active');
  if (pane) pane.classList.remove('hidden');

  trackGAEvent('tab_view', { tab_name: tabId });

  // Trigger chart resize if chart became visible
  if (tabId === 'parentLab' && parentCompareChartInstance) {
    parentCompareChartInstance.resize();
  }
  if (tabId === 'studentCalc' && studentTrajectoryChartInstance) {
    studentTrajectoryChartInstance.resize();
  }
}

// Mode Selector (Studying vs Graduated)
function setStudentMode(mode) {
  state.mode = mode;
  trackGAEvent('select_student_mode', { mode: mode });
  const btnStudying = document.getElementById('modeBtnStudying');
  const btnGraduated = document.getElementById('modeBtnGraduated');
  const studyingInputs = document.getElementById('studyingInputs');
  const graduatedInputs = document.getElementById('graduatedInputs');

  if (mode === 'studying') {
    btnStudying.className = 'px-3 py-1.5 rounded-lg bg-white shadow-sm text-blue-700 transition font-bold';
    btnGraduated.className = 'px-3 py-1.5 rounded-lg text-slate-600 hover:text-blue-600 transition';
    studyingInputs.classList.remove('hidden');
    graduatedInputs.classList.add('hidden');
  } else {
    btnGraduated.className = 'px-3 py-1.5 rounded-lg bg-white shadow-sm text-blue-700 transition font-bold';
    btnStudying.className = 'px-3 py-1.5 rounded-lg text-slate-600 hover:text-blue-600 transition';
    studyingInputs.classList.add('hidden');
    graduatedInputs.classList.remove('hidden');
  }

  // Adjust parent contribution options if graduated
  updateParentContributionOptions();
  runCalculation();
}

function updateParentContributionOptions() {
  const contribSelect = document.getElementById('inputContribType');
  const annualGroup = document.getElementById('parentAnnualGroup');
  const lumpGroup = document.getElementById('parentLumpGroup');

  if (state.mode === 'graduated') {
    contribSelect.value = 'lump_sum';
    contribSelect.options[0].disabled = true;
    contribSelect.options[1].disabled = true;
    annualGroup.classList.add('hidden');
    lumpGroup.classList.remove('hidden');
  } else {
    contribSelect.options[0].disabled = false;
    contribSelect.options[1].disabled = false;
    if (contribSelect.value === 'lump_sum') {
      annualGroup.classList.add('hidden');
      lumpGroup.classList.remove('hidden');
    } else {
      annualGroup.classList.remove('hidden');
      lumpGroup.classList.add('hidden');
    }
  }
}

// Quick Preset Helper
function applyPreset(presetName) {
  const presets = {
    nurse: { salary: 28400, growth: 2.5 },
    teacher: { salary: 30000, growth: 3.0 },
    median: { salary: 32500, growth: 3.5 },
    tech: { salary: 42000, growth: 5.0 },
    finance: { salary: 60000, growth: 6.0 },
  };

  const p = presets[presetName];
  if (!p) return;

  document.getElementById('inputSalary').value = p.salary;
  document.getElementById('inputSalaryGrowth').value = p.growth;
  document.getElementById('salaryGrowthVal').innerText = p.growth + '% / yr';

  trackGAEvent('select_preset', { preset: presetName, salary: p.salary });
  runCalculation();
}

// Quick Tuition & Maintenance Setters
function setTuition(val) {
  document.getElementById('inputTuition').value = val;
  runCalculation();
}

function setMaintenance(val) {
  document.getElementById('inputMaintenance').value = val;
  runCalculation();
}

// Read inputs from DOM into State
function readInputsFromDOM() {
  state.planType = document.getElementById('inputPlanType').value;
  state.tuition = parseFloat(document.getElementById('inputTuition').value) || 9250;
  state.maintenance = parseFloat(document.getElementById('inputMaintenance').value) || 10227;
  state.courseYears = parseInt(document.getElementById('inputCourseYears').value) || 3;
  state.gradBalance = parseFloat(document.getElementById('inputGradBalance').value) || 48000;
  state.salary = parseFloat(document.getElementById('inputSalary').value) || 32000;
  state.salaryGrowth = (parseFloat(document.getElementById('inputSalaryGrowth').value) || 3.5) / 100;
  state.rpi = (parseFloat(document.getElementById('inputRPI').value) || 4.1) / 100;
  state.hasPostgrad = document.getElementById('checkPostgrad').checked;

  state.contribType = document.getElementById('inputContribType').value;
  state.parentAnnual = parseFloat(document.getElementById('inputParentAnnual').value) || 9250;
  state.parentLump = parseFloat(document.getElementById('inputParentLump').value) || 25000;
  state.customMarketRate = (parseFloat(document.getElementById('inputCustomMarketRate').value) || 6.0) / 100;
  state.horizon = document.getElementById('inputHorizonYears').value;

  // Plan info text update
  const planInfo = PLAN_CONFIGS[state.planType]?.info || '';
  document.getElementById('planInfoText').innerText = planInfo;

  // Toggle parent input groups
  const annualGroup = document.getElementById('parentAnnualGroup');
  const lumpGroup = document.getElementById('parentLumpGroup');
  if (state.contribType === 'lump_sum') {
    annualGroup.classList.add('hidden');
    lumpGroup.classList.remove('hidden');
  } else {
    annualGroup.classList.remove('hidden');
    lumpGroup.classList.add('hidden');
  }
}

// Core Simulation Math
function calculateInStudyBalance(courseYears, tuition, maintenance, parentAnnualContrib, rpi, planType) {
  const netAnnualBorrow = Math.max(0, (tuition + maintenance) - parentAnnualContrib);
  let balance = 0;
  let studyRate = rpi;

  if (planType === 'plan_2') studyRate = Math.min(rpi + 0.03, 0.060); // Capped at 6.0% on GOV.UK
  else if (planType === 'plan_1') studyRate = Math.min(rpi, 0.041);

  for (let yr = 1; yr <= courseYears; yr++) {
    const interestExisting = balance * studyRate;
    const interestNew = netAnnualBorrow * (studyRate / 2.0);
    balance += netAnnualBorrow + interestExisting + interestNew;
  }

  return {
    graduationBalance: balance,
    totalBorrowed: netAnnualBorrow * courseYears,
    totalStudyInterest: balance - (netAnnualBorrow * courseYears),
  };
}

function getPostStudyInterestRate(planType, salary, rpi) {
  if (planType === 'plan_5') return rpi;
  if (planType === 'plan_2') {
    const lower = 29385;
    const upper = 52884;
    const cap = 0.060;
    const maxAddition = Math.max(0, Math.min(0.03, cap - rpi));
    if (salary <= lower) return rpi;
    if (salary >= upper) return rpi + maxAddition;
    const prop = (salary - lower) / (upper - lower);
    return rpi + (maxAddition * prop);
  }
  if (planType === 'plan_1') return Math.min(rpi, 0.041);
  return rpi;
}

function simulateLifetime(startBalance, startSalary, growthRate, planType, rpi, hasPostgrad) {
  const plan = PLAN_CONFIGS[planType] || PLAN_CONFIGS.plan_5;
  const threshold = plan.threshold;
  const rate = plan.rate;
  const writeOffYears = plan.writeOffYears;

  let balanceUG = startBalance;
  let balancePG = hasPostgrad ? 18000 : 0; // standard typical postgraduate master's balance

  let totalRepaidUG = 0;
  let totalRepaidPG = 0;
  let totalInterestUG = 0;
  let isPaidOff = false;
  let payoffYear = null;
  const schedule = [];

  for (let yr = 1; yr <= writeOffYears; yr++) {
    const salary = startSalary * Math.pow(1 + growthRate, yr - 1);
    const activeRate = getPostStudyInterestRate(planType, salary, rpi);

    // UG Repayment
    const eligibleUG = Math.max(0, salary - threshold);
    const expectedUG = eligibleUG * rate;

    // PG Repayment
    let expectedPG = 0;
    if (hasPostgrad && balancePG > 0) {
      const eligiblePG = Math.max(0, salary - POSTGRAD_CONFIG.threshold);
      expectedPG = eligiblePG * POSTGRAD_CONFIG.rate;
    }

    let actualUG = 0;
    let interestUG = 0;

    if (balanceUG > 0) {
      const maxPayable = balanceUG * (1 + activeRate);
      if (expectedUG >= maxPayable) {
        actualUG = maxPayable;
        interestUG = maxPayable - balanceUG;
        balanceUG = 0;
        if (!isPaidOff) {
          isPaidOff = true;
          payoffYear = yr;
        }
      } else {
        actualUG = expectedUG;
        interestUG = Math.max(0, (balanceUG - actualUG / 2) * activeRate);
        balanceUG = balanceUG + interestUG - actualUG;
        if (balanceUG <= 0.01) {
          balanceUG = 0;
          if (!isPaidOff) {
            isPaidOff = true;
            payoffYear = yr;
          }
        }
      }
    }

    totalRepaidUG += actualUG;
    totalInterestUG += interestUG;

    // PG balance update
    let actualPG = 0;
    if (hasPostgrad && balancePG > 0) {
      const pgRate = Math.min(rpi + 0.03, 0.060); // Capped at 6.0% as published on GOV.UK
      const maxPG = balancePG * (1 + pgRate);
      if (expectedPG >= maxPG) {
        actualPG = maxPG;
        balancePG = 0;
      } else {
        actualPG = expectedPG;
        const pgInterest = Math.max(0, (balancePG - actualPG / 2) * pgRate);
        balancePG = balancePG + pgInterest - actualPG;
      }
      totalRepaidPG += actualPG;
    }

    const totalAnnualRepay = actualUG + actualPG;

    schedule.push({
      year: yr,
      salary: salary,
      monthlyRepay: totalAnnualRepay / 12,
      annualRepayUG: actualUG,
      annualRepayPG: actualPG,
      totalAnnualRepay: totalAnnualRepay,
      cumulativeRepaid: totalRepaidUG + totalRepaidPG,
      interestRate: activeRate,
      interestAccruedUG: interestUG,
      balanceEndUG: balanceUG,
      balanceEndPG: balancePG,
      isPaidOff: isPaidOff,
    });
  }

  return {
    startBalance,
    totalRepaid: totalRepaidUG + totalRepaidPG,
    totalRepaidUG,
    totalInterestUG,
    writtenOffUG: balanceUG,
    isPaidOff,
    payoffYear,
    writeOffYears,
    schedule,
  };
}

// Compound Investment Calculator (3%, 4%, 5%, custom)
function calculateCompoundPot(annualContribs, lumpSum, rate, totalYears) {
  let pot = lumpSum;
  const trajectory = [];

  for (let yr = 1; yr <= totalYears; yr++) {
    const c = yr <= annualContribs.length ? annualContribs[yr - 1] : 0;
    pot = (pot + c) * (1 + rate);
    trajectory.push(pot);
  }
  return trajectory;
}

// UK Income Tax & National Insurance (England & Wales 2024-2026)
function calculateTaxAndNI(grossSalary, studentLoanAnnual) {
  let personalAllowance = 12570;
  if (grossSalary > 100000) {
    personalAllowance = Math.max(0, personalAllowance - (grossSalary - 100000) / 2);
  }

  const taxableIncome = Math.max(0, grossSalary - personalAllowance);
  let tax = 0;
  const basicBand = 50270 - 12570;
  const higherBand = 125140 - 50270;

  if (taxableIncome > 0) {
    const basicPart = Math.min(taxableIncome, basicBand);
    tax += basicPart * 0.20;

    if (taxableIncome > basicBand) {
      const higherPart = Math.min(taxableIncome - basicBand, higherBand);
      tax += higherPart * 0.40;

      if (taxableIncome > (basicBand + higherBand)) {
        const addPart = taxableIncome - (basicBand + higherBand);
        tax += addPart * 0.45;
      }
    }
  }

  // National Insurance 8% (below £50,270) and 2% above
  let ni = 0;
  if (grossSalary > 12570) {
    const mainNI = Math.min(grossSalary, 50270) - 12570;
    ni += mainNI * 0.08;
    if (grossSalary > 50270) {
      ni += (grossSalary - 50270) * 0.02;
    }
  }

  const netAnnual = Math.max(0, grossSalary - tax - ni - studentLoanAnnual);

  let marginalTax = grossSalary <= 50270 ? 0.20 : (grossSalary <= 125140 ? 0.40 : 0.45);
  if (grossSalary > 100000 && grossSalary <= 125140) marginalTax = 0.60;
  const marginalNI = grossSalary <= 50270 ? 0.08 : 0.02;
  const marginalSL = 0.09;
  const marginalTotal = (marginalTax + marginalNI + marginalSL) * 100;

  return {
    grossAnnual: grossSalary,
    grossMonthly: grossSalary / 12,
    taxAnnual: tax,
    taxMonthly: tax / 12,
    niAnnual: ni,
    niMonthly: ni / 12,
    slAnnual: studentLoanAnnual,
    slMonthly: studentLoanAnnual / 12,
    netAnnual: netAnnual,
    netMonthly: netAnnual / 12,
    marginalRate: marginalTotal,
  };
}

// Master Run Calculation
function runCalculation() {
  readInputsFromDOM();

  // 1. In-study balance calculations
  let baseGradBalance = 0;
  let contribGradBalance = 0;
  let parentOutlayTotal = 0;
  let parentFlow = [];
  let studyInterest = 0;

  const maxHorizon = PLAN_CONFIGS[state.planType]?.writeOffYears || 40;
  const simYears = state.horizon === 'write_off' ? maxHorizon : parseInt(state.horizon);

  if (state.mode === 'studying') {
    // Base: No help
    const baseStudy = calculateInStudyBalance(
      state.courseYears, state.tuition, state.maintenance, 0, state.rpi, state.planType
    );
    baseGradBalance = baseStudy.graduationBalance;
    studyInterest = baseStudy.totalStudyInterest;

    // Contrib: Parent helps
    let parentAnnualPortion = 0;
    let parentLumpPortion = 0;

    if (state.contribType === 'annual_fee') {
      parentAnnualPortion = state.tuition;
      parentOutlayTotal = state.tuition * state.courseYears;
      parentFlow = Array(state.courseYears).fill(state.tuition);
    } else if (state.contribType === 'custom_annual') {
      parentAnnualPortion = state.parentAnnual;
      parentOutlayTotal = state.parentAnnual * state.courseYears;
      parentFlow = Array(state.courseYears).fill(state.parentAnnual);
    } else { // lump sum
      parentLumpPortion = state.parentLump;
      parentOutlayTotal = state.parentLump;
      parentFlow = [state.parentLump];
    }

    const contribStudy = calculateInStudyBalance(
      state.courseYears, state.tuition, state.maintenance,
      state.contribType === 'lump_sum' ? (parentLumpPortion / state.courseYears) : parentAnnualPortion,
      state.rpi, state.planType
    );
    contribGradBalance = contribStudy.graduationBalance;

  } else {
    // Graduated mode
    baseGradBalance = state.gradBalance;
    parentOutlayTotal = state.parentLump;
    parentFlow = [parentOutlayTotal];
    contribGradBalance = Math.max(0, state.gradBalance - state.parentLump);
  }

  // 2. Lifetime simulations
  const simBase = simulateLifetime(
    baseGradBalance, state.salary, state.salaryGrowth, state.planType, state.rpi, state.hasPostgrad
  );
  const simContrib = simulateLifetime(
    contribGradBalance, state.salary, state.salaryGrowth, state.planType, state.rpi, state.hasPostgrad
  );

  // 3. Market Growth calculations (3%, 4%, 5%, custom)
  let annualMarketFlow = [];
  let initialMarketLump = 0;

  if (state.mode === 'studying' && state.contribType !== 'lump_sum') {
    annualMarketFlow = [...parentFlow];
    while (annualMarketFlow.length < maxHorizon) annualMarketFlow.push(0);
    initialMarketLump = 0;
  } else {
    annualMarketFlow = Array(maxHorizon).fill(0);
    initialMarketLump = parentOutlayTotal;
  }

  const pot3 = calculateCompoundPot(annualMarketFlow, initialMarketLump, 0.03, maxHorizon);
  const pot4 = calculateCompoundPot(annualMarketFlow, initialMarketLump, 0.04, maxHorizon);
  const pot5 = calculateCompoundPot(annualMarketFlow, initialMarketLump, 0.05, maxHorizon);
  const potCustom = calculateCompoundPot(annualMarketFlow, initialMarketLump, state.customMarketRate, maxHorizon);

  // 4. Savings and Deltas
  const repaymentsSaved = simBase.totalRepaid - simContrib.totalRepaid;
  const interestSaved = simBase.totalInterestUG - simContrib.totalInterestUG;
  const yearsEarlier = (simContrib.isPaidOff && simBase.isPaidOff)
    ? Math.max(0, simBase.payoffYear - simContrib.payoffYear)
    : (simContrib.isPaidOff ? (maxHorizon - simContrib.payoffYear) : 0);
  const netFamilyGain = repaymentsSaved - parentOutlayTotal;

  // 5. Update UI Components
  updateParentDashboard({
    parentOutlayTotal,
    baseGradBalance,
    contribGradBalance,
    simBase,
    simContrib,
    repaymentsSaved,
    interestSaved,
    yearsEarlier,
    netFamilyGain,
    pot3,
    pot4,
    pot5,
    potCustom,
    maxHorizon,
    simYears,
  });

  updateStudentDashboard(simBase, baseGradBalance, studyInterest);
  updateTimelineMilestoneTable(simBase, simContrib, pot3, pot4, pot5, potCustom, maxHorizon);
  updateFullScheduleTable(simBase, pot3, pot4, pot5, maxHorizon);

  // 6. Render Charts
  renderParentComparisonChart(simBase, simContrib, pot3, pot4, pot5, potCustom, maxHorizon);
  renderStudentTrajectoryChart(simBase);
}

// Update Parental Contribution Dashboard
function updateParentDashboard(data) {
  // Stat Badges
  document.getElementById('statTotalParentContribution').innerText = `£${data.parentOutlayTotal.toLocaleString('en-GB', { maximumFractionDigits: 0 })}`;
  if (state.mode === 'studying' && state.contribType === 'annual_fee') {
    document.getElementById('statParentFlowDesc').innerText = `£${state.tuition.toLocaleString()} / yr × ${state.courseYears} yrs`;
  } else if (state.mode === 'studying' && state.contribType === 'custom_annual') {
    document.getElementById('statParentFlowDesc').innerText = `£${state.parentAnnual.toLocaleString()} / yr × ${state.courseYears} yrs`;
  } else {
    document.getElementById('statParentFlowDesc').innerText = `Lump sum paid upfront`;
  }

  // Column A: Without Parental Help
  document.getElementById('colA_startBalance').innerText = `£${Math.round(data.baseGradBalance).toLocaleString('en-GB')}`;
  document.getElementById('colA_totalRepaid').innerText = `£${Math.round(data.simBase.totalRepaid).toLocaleString('en-GB')}`;
  document.getElementById('colA_interest').innerText = `£${Math.round(data.simBase.totalInterestUG).toLocaleString('en-GB')}`;
  if (data.simBase.isPaidOff) {
    document.getElementById('colA_payoffStatus').innerText = `Paid Off (Yr ${data.simBase.payoffYear})`;
    document.getElementById('colA_payoffStatus').className = 'font-bold text-emerald-600';
    document.getElementById('colA_writtenOff').innerText = `£0 (Cleared in full)`;
  } else {
    document.getElementById('colA_payoffStatus').innerText = `Written Off (Yr ${data.maxHorizon})`;
    document.getElementById('colA_payoffStatus').className = 'font-bold text-amber-600';
    document.getElementById('colA_writtenOff').innerText = `£${Math.round(data.simBase.writtenOffUG).toLocaleString('en-GB')}`;
  }

  // Column B: With Parental Help
  document.getElementById('colB_parentPaid').innerText = `£${Math.round(data.parentOutlayTotal).toLocaleString('en-GB')}`;
  document.getElementById('colB_startBalance').innerText = `£${Math.round(data.contribGradBalance).toLocaleString('en-GB')}`;
  document.getElementById('colB_totalRepaid').innerText = `£${Math.round(data.simContrib.totalRepaid).toLocaleString('en-GB')}`;
  if (data.simContrib.isPaidOff) {
    document.getElementById('colB_payoffStatus').innerText = `Paid Off (Yr ${data.simContrib.payoffYear})`;
    document.getElementById('colB_payoffStatus').className = 'font-bold text-emerald-600';
  } else {
    document.getElementById('colB_payoffStatus').innerText = `Written Off (Yr ${data.maxHorizon})`;
    document.getElementById('colB_payoffStatus').className = 'font-bold text-blue-800';
  }

  document.getElementById('colB_savings').innerText = `£${Math.round(data.repaymentsSaved).toLocaleString('en-GB')}`;
  document.getElementById('colB_yearsEarlier').innerText = `${data.yearsEarlier} years`;

  const netGainEl = document.getElementById('colB_netGain');
  if (data.netFamilyGain >= 0) {
    netGainEl.innerText = `+£${Math.round(data.netFamilyGain).toLocaleString('en-GB')}`;
    netGainEl.className = 'font-bold text-emerald-600';
  } else {
    netGainEl.innerText = `-£${Math.round(Math.abs(data.netFamilyGain)).toLocaleString('en-GB')}`;
    netGainEl.className = 'font-bold text-red-600';
  }

  // Column C: Market Pot
  document.getElementById('colC_capitalInvested').innerText = `£${Math.round(data.parentOutlayTotal).toLocaleString('en-GB')}`;
  const horizonIdx = data.simYears - 1;
  document.getElementById('colC_pot3').innerText = `£${Math.round(data.pot3[horizonIdx] || data.pot3[data.pot3.length - 1]).toLocaleString('en-GB')}`;
  document.getElementById('colC_pot4').innerText = `£${Math.round(data.pot4[horizonIdx] || data.pot4[data.pot4.length - 1]).toLocaleString('en-GB')}`;
  document.getElementById('colC_pot5').innerText = `£${Math.round(data.pot5[horizonIdx] || data.pot5[data.pot5.length - 1]).toLocaleString('en-GB')}`;
  document.getElementById('colC_customRateLabel').innerText = `${(state.customMarketRate * 100).toFixed(1)}% p.a.`;
  document.getElementById('colC_potCustom').innerText = `£${Math.round(data.potCustom[horizonIdx] || data.potCustom[data.potCustom.length - 1]).toLocaleString('en-GB')}`;

  // Strategic Verdict Box
  const verdictBox = document.getElementById('verdictBox');
  const verdictIcon = document.getElementById('verdictIcon');
  const verdictTitle = document.getElementById('verdictTitle');
  const verdictBadge = document.getElementById('verdictBadge');
  const verdictSummary = document.getElementById('verdictSummary');
  const verdictRec = document.getElementById('verdictRecommendation');

  const potAt20 = Math.round(data.pot5[19] || data.pot5[data.pot5.length - 1]);
  const potAtEnd = Math.round(data.pot5[horizonIdx] || data.pot5[data.pot5.length - 1]);

  if (!data.simBase.isPaidOff && !data.simContrib.isPaidOff) {
    // Both written off -> Huge Tax Trap!
    verdictBox.className = 'rounded-2xl p-6 border shadow-sm transition-all duration-300 bg-amber-50 border-amber-300';
    verdictIcon.innerText = '⚠️';
    verdictTitle.innerText = 'High Risk of Wasted Parental Capital (Graduate Tax Trap)';
    verdictBadge.innerText = 'Ineffective Outlay';
    verdictBadge.className = 'text-xs font-bold px-2.5 py-1 rounded-full bg-red-100 text-red-800';
    verdictSummary.innerHTML = `Under this expected career trajectory, the student <strong>never clears the loan</strong> before statutory cancellation at Year ${data.maxHorizon}. Because repayments depend strictly on salary (not debt size), paying £${data.parentOutlayTotal.toLocaleString()} upfront reduces the student's monthly deductions by <strong class="text-red-600">£${Math.round(data.repaymentsSaved).toLocaleString()}</strong>. Your contribution simply subsidies HMRC write-off debt!`;
    verdictRec.innerHTML = `Strongly advise <strong>AGAINST paying tuition fees upfront</strong>. Instead, invest that £${data.parentOutlayTotal.toLocaleString()} in a <strong>Stocks & Shares ISA or Lifetime ISA</strong>. Compounding at 5% p.a., it will grow into <strong>£${potAt20.toLocaleString()}</strong> by Year 20, providing a life-changing house deposit or safety net that remains in the family!`;
  } else if (!data.simBase.isPaidOff && data.simContrib.isPaidOff) {
    // Partial benefit
    verdictBox.className = 'rounded-2xl p-6 border shadow-sm transition-all duration-300 bg-blue-50 border-blue-300';
    verdictIcon.innerText = '⚖️';
    verdictTitle.innerText = 'Mixed Benefit: Loan Cleared, But Weigh Flexibility vs Liquid ISA';
    verdictBadge.innerText = 'Crossover Case';
    verdictBadge.className = 'text-xs font-bold px-2.5 py-1 rounded-full bg-blue-100 text-blue-800';
    verdictSummary.innerHTML = `With your £${data.parentOutlayTotal.toLocaleString()} contribution, the loan is paid off in <strong>Year ${data.simContrib.payoffYear}</strong> (saving the student £${Math.round(data.repaymentsSaved).toLocaleString()} in lifetime deductions). Net family financial impact is <strong>£${Math.round(data.netFamilyGain).toLocaleString()}</strong>.`;
    verdictRec.innerHTML = `Evaluate whether having <strong>liquid cash (£${potAtEnd.toLocaleString()} at 5% growth)</strong> in an ISA for buying a first home in their 20s or 30s is more valuable than locking that cash into wiping out Student Finance England debt.`;
  } else {
    // High Earner
    verdictBox.className = 'rounded-2xl p-6 border shadow-sm transition-all duration-300 bg-emerald-50 border-emerald-300';
    verdictIcon.innerText = '✅';
    verdictTitle.innerText = 'Solid Paydown Return for High Earner';
    verdictBadge.innerText = 'Financially Effective';
    verdictBadge.className = 'text-xs font-bold px-2.5 py-1 rounded-full bg-emerald-100 text-emerald-800';
    verdictSummary.innerHTML = `The student's earnings are high enough to clear the loan in both cases. Your £${data.parentOutlayTotal.toLocaleString()} contribution saves <strong>£${Math.round(data.interestSaved).toLocaleString()} in compound interest</strong> and clears the debt <strong>${data.yearsEarlier} years earlier</strong>!`;
    verdictRec.innerHTML = `Under this high-earner path where the loan is cleared before write-off, reducing the principal avoids compounding interest, generating an effective return matching the loan rate. However, this outcome is conditional on sustained high earnings over a multi-decade career; voluntary repayments cannot be refunded if earnings decrease.`;
  }
}

// Update Student Repayment Dashboard
function updateStudentDashboard(sim, gradBalance, studyInterest = 0) {
  // Initial Payslip
  const firstYearRepay = sim.schedule[0]?.totalAnnualRepay || 0;
  const payslip = calculateTaxAndNI(state.salary, firstYearRepay);

  document.getElementById('payslipGrossDisplay').innerText = `£${Math.round(payslip.grossAnnual).toLocaleString()} / yr`;
  document.getElementById('payslipGrossMonthlyDisplay').innerText = `£${Math.round(payslip.grossMonthly).toLocaleString()} / mo`;
  document.getElementById('payslipTaxDisplay').innerText = `£${Math.round(payslip.taxMonthly).toLocaleString()} / mo`;
  document.getElementById('payslipTaxAnnualDisplay').innerText = `£${Math.round(payslip.taxAnnual).toLocaleString()} / yr`;
  document.getElementById('payslipNIDisplay').innerText = `£${Math.round(payslip.niMonthly).toLocaleString()} / mo`;
  document.getElementById('payslipNIAnnualDisplay').innerText = `£${Math.round(payslip.niAnnual).toLocaleString()} / yr`;
  document.getElementById('payslipSLDisplay').innerText = `£${Math.round(payslip.slMonthly).toLocaleString()} / mo`;
  document.getElementById('payslipSLAnnualDisplay').innerText = `£${Math.round(payslip.slAnnual).toLocaleString()} / yr`;
  document.getElementById('payslipNetDisplay').innerText = `£${Math.round(payslip.netMonthly).toLocaleString()} / mo`;
  document.getElementById('payslipNetAnnualDisplay').innerText = `£${Math.round(payslip.netAnnual).toLocaleString()} / yr`;
  document.getElementById('payslipMarginalRate').innerText = `${payslip.marginalRate.toFixed(1)}%`;
  document.getElementById('payslipThresholdVal').innerText = `£${(PLAN_CONFIGS[state.planType]?.threshold || 25000).toLocaleString()}`;

  // KPI Cards
  document.getElementById('kpiStartBalance').innerText = `£${Math.round(gradBalance).toLocaleString()}`;
  const studyInterestEl = document.getElementById('kpiInStudyInterest');
  if (studyInterestEl) {
    if (state.mode === 'studying') {
      studyInterestEl.innerText = `Includes £${Math.round(studyInterest).toLocaleString()} in-study interest (${state.courseYears} yrs)`;
    } else {
      studyInterestEl.innerText = 'Entered graduation balance';
    }
  }
  document.getElementById('kpiTotalRepaid').innerText = `£${Math.round(sim.totalRepaid).toLocaleString()}`;
  const ratio = Math.round((sim.totalRepaid / Math.max(1, gradBalance)) * 100);
  document.getElementById('kpiRepaidRatio').innerText = `${ratio}% of original debt repaid`;
  document.getElementById('kpiTotalInterest').innerText = `£${Math.round(sim.totalInterestUG).toLocaleString()}`;

  if (sim.isPaidOff) {
    document.getElementById('kpiPayoffOutcome').innerText = `Paid Off (Yr ${sim.payoffYear})`;
    document.getElementById('kpiPayoffOutcome').className = 'text-2xl font-black text-emerald-600 block mt-1';
    document.getElementById('kpiWrittenOffAmount').innerText = 'Cleared in full by graduate';
  } else {
    document.getElementById('kpiPayoffOutcome').innerText = `Written Off`;
    document.getElementById('kpiPayoffOutcome').className = 'text-2xl font-black text-blue-600 block mt-1';
    document.getElementById('kpiWrittenOffAmount').innerText = `£${Math.round(sim.writtenOffUG).toLocaleString()} cancelled by Gov (Yr ${sim.writeOffYears})`;
  }
}

// Milestone Breakdown Table
function updateTimelineMilestoneTable(simBase, simContrib, pot3, pot4, pot5, potCustom, maxHorizon) {
  const tbody = document.getElementById('milestoneTableBody');
  tbody.innerHTML = '';

  const milestones = [
    { label: 'Uni End (Course Finish)', yr: state.mode === 'studying' ? state.courseYears : 1 },
    { label: 'Year 5 Post-Grad (Age ~26)', yr: 5 },
    { label: 'Year 10 Post-Grad (Age ~31 - House Buy)', yr: 10 },
    { label: 'Year 15 Post-Grad (Age ~36)', yr: 15 },
    { label: 'Year 20 Post-Grad (Age ~41 - Mid Career)', yr: 20 },
    { label: 'Year 30 Post-Grad (Plan 2 Write-Off)', yr: 30 },
  ];

  if (maxHorizon >= 40) {
    milestones.push({ label: 'Year 40 Post-Grad (Plan 5 Write-Off)', yr: 40 });
  }

  milestones.forEach(m => {
    const yrIdx = Math.min(m.yr, maxHorizon) - 1;
    const baseCumulative = simBase.schedule[yrIdx]?.cumulativeRepaid || 0;
    const contribCumulative = simContrib.schedule[yrIdx]?.cumulativeRepaid || 0;
    const loanSavings = Math.max(0, baseCumulative - contribCumulative);

    const val3 = pot3[yrIdx] || 0;
    const val4 = pot4[yrIdx] || 0;
    const val5 = pot5[yrIdx] || 0;
    const valCustom = potCustom[yrIdx] || 0;

    const row = document.createElement('tr');
    row.className = 'hover:bg-slate-50 transition';
    row.innerHTML = `
      <td class="py-2.5 px-3 font-semibold text-slate-800">${m.label}</td>
      <td class="py-2.5 px-3 font-bold text-blue-700">£${Math.round(loanSavings).toLocaleString()}</td>
      <td class="py-2.5 px-3 font-semibold text-emerald-700">£${Math.round(val3).toLocaleString()}</td>
      <td class="py-2.5 px-3 font-semibold text-emerald-700">£${Math.round(val4).toLocaleString()}</td>
      <td class="py-2.5 px-3 font-bold text-emerald-800">£${Math.round(val5).toLocaleString()}</td>
      <td class="py-2.5 px-3 font-semibold text-indigo-700">£${Math.round(valCustom).toLocaleString()}</td>
    `;
    tbody.appendChild(row);
  });
}

// Full Year-by-Year Schedule Table
function updateFullScheduleTable(sim, pot3, pot4, pot5, maxHorizon) {
  const tbody = document.getElementById('fullScheduleTableBody');
  tbody.innerHTML = '';

  sim.schedule.forEach(row => {
    const yrIdx = row.year - 1;
    const tr = document.createElement('tr');
    tr.className = row.isPaidOff && row.balanceEndUG === 0 ? 'bg-emerald-50/40 hover:bg-emerald-50' : 'hover:bg-slate-50';

    tr.innerHTML = `
      <td class="py-2 px-3 font-bold">${row.year}</td>
      <td class="py-2 px-3 text-slate-500">${21 + row.year}</td>
      <td class="py-2 px-3 font-semibold text-slate-800">£${Math.round(row.salary).toLocaleString()}</td>
      <td class="py-2 px-3 text-slate-700">£${Math.round(row.monthlyRepay).toLocaleString()}</td>
      <td class="py-2 px-3 font-bold text-blue-600">£${Math.round(row.totalAnnualRepay).toLocaleString()}</td>
      <td class="py-2 px-3 text-slate-600">${(row.interestRate * 100).toFixed(1)}%</td>
      <td class="py-2 px-3 text-slate-600">£${Math.round(row.interestAccruedUG).toLocaleString()}</td>
      <td class="py-2 px-3 font-bold ${row.balanceEndUG === 0 ? 'text-emerald-600' : 'text-red-600'}">
        £${Math.round(row.balanceEndUG).toLocaleString()}
      </td>
      <td class="py-2 px-3 text-emerald-700">£${Math.round(pot3[yrIdx] || 0).toLocaleString()}</td>
      <td class="py-2 px-3 text-emerald-700">£${Math.round(pot4[yrIdx] || 0).toLocaleString()}</td>
      <td class="py-2 px-3 text-emerald-800 font-semibold">£${Math.round(pot5[yrIdx] || 0).toLocaleString()}</td>
    `;
    tbody.appendChild(tr);
  });
}

// Chart 1: Parental Comparison Chart (Chart.js)
function renderParentComparisonChart(simBase, simContrib, pot3, pot4, pot5, potCustom, maxHorizon) {
  const ctx = document.getElementById('parentCompareChart')?.getContext('2d');
  if (!ctx) return;

  const labels = [];
  const savingsData = [];
  const pot3Data = [];
  const pot4Data = [];
  const pot5Data = [];
  const potCustomData = [];

  for (let yr = 1; yr <= maxHorizon; yr++) {
    labels.push(`Yr ${yr}`);
    const yrIdx = yr - 1;
    const baseRepaid = simBase.schedule[yrIdx]?.cumulativeRepaid || 0;
    const contribRepaid = simContrib.schedule[yrIdx]?.cumulativeRepaid || 0;
    savingsData.push(Math.round(Math.max(0, baseRepaid - contribRepaid)));
    pot3Data.push(Math.round(pot3[yrIdx] || 0));
    pot4Data.push(Math.round(pot4[yrIdx] || 0));
    pot5Data.push(Math.round(pot5[yrIdx] || 0));
    potCustomData.push(Math.round(potCustom[yrIdx] || 0));
  }

  if (parentCompareChartInstance) {
    parentCompareChartInstance.destroy();
  }

  parentCompareChartInstance = new Chart(ctx, {
    type: 'line',
    data: {
      labels: labels,
      datasets: [
        {
          label: 'Student Loan Repayments Saved (£)',
          data: savingsData,
          borderColor: '#2563eb',
          backgroundColor: 'rgba(37, 99, 235, 0.1)',
          borderWidth: 3,
          fill: true,
          tension: 0.2,
        },
        {
          label: 'Market Investment Pot @ 3% (£)',
          data: pot3Data,
          borderColor: '#34d399',
          borderWidth: 2,
          borderDash: [5, 5],
          fill: false,
          tension: 0.2,
        },
        {
          label: 'Market Investment Pot @ 4% (£)',
          data: pot4Data,
          borderColor: '#059669',
          borderWidth: 2,
          borderDash: [4, 4],
          fill: false,
          tension: 0.2,
        },
        {
          label: 'Market Investment Pot @ 5% (£)',
          data: pot5Data,
          borderColor: '#064e3b',
          borderWidth: 3,
          fill: false,
          tension: 0.2,
        },
        {
          label: `Market Pot @ ${(state.customMarketRate * 100).toFixed(0)}% (Custom)`,
          data: potCustomData,
          borderColor: '#7c3aed',
          borderWidth: 2,
          fill: false,
          tension: 0.2,
        }
      ]
    },
    options: {
      responsive: true,
      maintainAspectRatio: false,
      interaction: {
        mode: 'index',
        intersect: false,
      },
      plugins: {
        legend: {
          position: 'top',
          labels: { boxWidth: 12, font: { size: 11 } }
        },
        tooltip: {
          callbacks: {
            label: (ctx) => `${ctx.dataset.label}: £${ctx.parsed.y.toLocaleString()}`
          }
        }
      },
      scales: {
        y: {
          beginAtZero: true,
          ticks: {
            callback: (v) => '£' + (v >= 1000 ? (v / 1000) + 'k' : v)
          },
          grid: { color: '#f1f5f9' }
        },
        x: {
          grid: { display: false }
        }
      }
    }
  });
}

// Chart 2: Student Lifetime Trajectory Chart
function renderStudentTrajectoryChart(sim) {
  const ctx = document.getElementById('studentTrajectoryChart')?.getContext('2d');
  if (!ctx) return;

  const labels = sim.schedule.map(s => `Yr ${s.year}`);
  const balanceData = sim.schedule.map(s => Math.round(s.balanceEndUG));
  const annualRepayData = sim.schedule.map(s => Math.round(s.totalAnnualRepay));
  const cumRepaidData = sim.schedule.map(s => Math.round(s.cumulativeRepaid));

  if (studentTrajectoryChartInstance) {
    studentTrajectoryChartInstance.destroy();
  }

  studentTrajectoryChartInstance = new Chart(ctx, {
    type: 'line',
    data: {
      labels: labels,
      datasets: [
        {
          label: 'Remaining Loan Balance (£)',
          data: balanceData,
          borderColor: '#ef4444',
          backgroundColor: 'rgba(239, 68, 68, 0.08)',
          borderWidth: 2.5,
          fill: true,
          tension: 0.2,
        },
        {
          label: 'Annual Student Repayment (£)',
          data: annualRepayData,
          borderColor: '#2563eb',
          borderWidth: 2,
          fill: false,
          tension: 0.2,
        },
        {
          label: 'Cumulative Total Repaid (£)',
          data: cumRepaidData,
          borderColor: '#10b981',
          borderWidth: 2,
          borderDash: [4, 4],
          fill: false,
          tension: 0.2,
        }
      ]
    },
    options: {
      responsive: true,
      maintainAspectRatio: false,
      interaction: {
        mode: 'index',
        intersect: false,
      },
      plugins: {
        legend: {
          position: 'top',
          labels: { boxWidth: 12, font: { size: 11 } }
        },
        tooltip: {
          callbacks: {
            label: (ctx) => `${ctx.dataset.label}: £${ctx.parsed.y.toLocaleString()}`
          }
        }
      },
      scales: {
        y: {
          beginAtZero: true,
          ticks: {
            callback: (v) => '£' + (v >= 1000 ? (v / 1000) + 'k' : v)
          },
          grid: { color: '#f1f5f9' }
        },
        x: {
          grid: { display: false }
        }
      }
    }
  });
}

// Export Full Schedule to CSV
function exportToCSV() {
  const maxHorizon = PLAN_CONFIGS[state.planType]?.writeOffYears || 40;
  const sim = simulateLifetime(
    state.mode === 'studying'
      ? calculateInStudyBalance(state.courseYears, state.tuition, state.maintenance, 0, state.rpi, state.planType).graduationBalance
      : state.gradBalance,
    state.salary, state.salaryGrowth, state.planType, state.rpi, state.hasPostgrad
  );

  const annualFlow = state.mode === 'studying' && state.contribType !== 'lump_sum'
    ? Array(state.courseYears).fill(state.tuition)
    : Array(maxHorizon).fill(0);
  const lump = (state.mode === 'studying' && state.contribType === 'lump_sum') || state.mode === 'graduated'
    ? state.parentLump
    : 0;

  const pot3 = calculateCompoundPot(annualFlow, lump, 0.03, maxHorizon);
  const pot4 = calculateCompoundPot(annualFlow, lump, 0.04, maxHorizon);
  const pot5 = calculateCompoundPot(annualFlow, lump, 0.05, maxHorizon);

  let csv = 'Year,Approx Age,Projected Salary,Monthly Repay,Annual Repay,Cumulative Repaid,Interest Rate %,Interest Accrued,Remaining Balance,Market Pot 3%,Market Pot 4%,Market Pot 5%\n';

  sim.schedule.forEach((row, idx) => {
    csv += [
      row.year,
      21 + row.year,
      Math.round(row.salary),
      Math.round(row.monthlyRepay),
      Math.round(row.totalAnnualRepay),
      Math.round(row.cumulativeRepaid),
      (row.interestRate * 100).toFixed(2),
      Math.round(row.interestAccruedUG),
      Math.round(row.balanceEndUG),
      Math.round(pot3[idx] || 0),
      Math.round(pot4[idx] || 0),
      Math.round(pot5[idx] || 0),
    ].join(',') + '\n';
  });

  const blob = new Blob([csv], { type: 'text/csv;charset=utf-8;' });
  const url = URL.createObjectURL(blob);
  const a = document.createElement('a');
  a.href = url;
  a.download = `UK_Student_Loan_Schedule_${state.planType}.csv`;
  trackGAEvent('export_csv', { plan_type: state.planType });
  document.body.appendChild(a);
  a.click();
  document.body.removeChild(a);
}
