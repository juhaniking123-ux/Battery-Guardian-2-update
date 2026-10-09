#!/usr/bin/env python3
"""Deterministic one-time patch against the known v2.0.11 source archive."""
from pathlib import Path
import sys

root=Path(sys.argv[1])
src=root/"app/src/main/java/com/mec/batteryguardian2"

def change(file,old,new):
    p=src/file
    x=p.read_text(encoding="utf-8")
    if old not in x:
        raise RuntimeError("v2.0.11 source mismatch: "+str(file))
    p.write_text(x.replace(old,new),encoding="utf-8")

change("MainActivity.java",
'''        NotificationUtil.ensureChannels(this);
        shizuku = ShizukuBridge.get(this);''',
'''        NotificationUtil.ensureChannels(this);
        if (AppPrefs.autoManage(this)) AutoManageJobService.schedule(this);
        if (!StandbyDrainTest.running(this) && !ExperimentController.running(this)) MonitorService.stop(this);
        shizuku = ShizukuBridge.get(this);''')

change("MainActivity.java",
'''                try { MonitorService.start(this); } catch (Exception e) { toastDialog("자동 관리 시작 실패",e.getMessage()); }
            } else if (!StandbyDrainTest.running(this) && !ExperimentController.running(this)) MonitorService.stop(this);''',
'''                AutoManageJobService.schedule(this);
            } else {
                AutoManageJobService.cancel(this);
                if (!StandbyDrainTest.running(this) && !ExperimentController.running(this)) MonitorService.stop(this);
            }''')

change("MainActivity.java",
'''        MonitorService.stop(this);
        insight.setText("Guardian이 적용했던 설정을 원상복구하고 있습니다...");''',
'''        MonitorService.stop(this);
        AutoManageJobService.cancel(this);
        insight.setText("Guardian이 적용했던 설정을 원상복구하고 있습니다...");''')

change("MainActivity.java",
'''        AppPrefs.setAutoManage(this,false);
        AppPrefs.setRestoreMode(this,true);''',
'''        AppPrefs.setAutoManage(this,false);
        AutoManageJobService.cancel(this);
        AppPrefs.setRestoreMode(this,true);''')

change("MainActivity.java",'"실제 절감 효과: 아직 학습 중"','"실제 절감 효과: 아직 측정 결과 없음"')
change("MainActivity.java",
'''            return "학습 진행: 7일 / 7일 · 100% 완료 ✓\\n현재 상태: 지속 학습 중 · 사용 패턴 변화 반영 중";''',
'''            return "초기 관찰 기간: 7일 / 7일 · 100% 완료 ✓\\n현재 상태: 완료 · 자동 관리는 충전/대기 중 저빈도로 실행";''')
change("MainActivity.java","Battery Guardian 2  ·  v2.0.11  ·  Rule Engine 2","Battery Guardian 2  ·  v2.0.12  ·  Rule Engine 2")

change("BootReceiver.java",
'''if (AppPrefs.autoManage(context)) { try { MonitorService.start(context); } catch (Exception ignored) {} }''',
'''if (AppPrefs.autoManage(context)) { try { AutoManageJobService.schedule(context); } catch (Exception ignored) {} }''')

change("MonitorService.java",
'''            try {
                ShizukuBridge.get(MonitorService.this).ensureBound();''',
'''            try {
                if (!ExperimentController.running(MonitorService.this) && !StandbyDrainTest.running(MonitorService.this)) {
                    stopSelf();
                    return;
                }
                ShizukuBridge.get(MonitorService.this).ensureBound();''')
change("MonitorService.java",
'''                if (!AppPrefs.restoreMode(MonitorService.this)) {
                    PowerActions.restoreCriticalNotifications(MonitorService.this);
                    PowerActions.restoreReusedApps(MonitorService.this);
                }
''',"")
p=src/"MonitorService.java"
x=p.read_text(encoding="utf-8")
a=x.index('                long now = System.currentTimeMillis();')
b=x.index('                String extra = StandbyDrainTest.running',a)
x=x[:a]+x[b:]
x=x.replace('!AppPrefs.autoManage(MonitorService.this) && !ExperimentController.running','!ExperimentController.running')
x=x.replace('Math.max(1, rules.sampleMinutes)','Math.max(5, rules.sampleMinutes)')
p.write_text(x,encoding="utf-8")

p=src/"PowerActions.java"
x=p.read_text(encoding="utf-8")
a=x.index('    public static int restoreCriticalNotifications(Context c) {')
b=x.index('    public static final class RestoreSummary',a)
x=x[:a]+'''    public static int restoreCriticalNotifications(Context c) {
        // Versions before v2.0.12 repeatedly changed these settings.
        // Restore normal OS app-ops once, preserving protected-app records.
        SharedPreferences p=AppPrefs.p(c);
        if (AppPrefs.restoreMode(c) || p.getBoolean("guardian_v212_notification_cleanup",false)
                || !p.getBoolean("critical_notification_fix_v210_done",false)) return 0;
        ShizukuBridge bridge=ShizukuBridge.get(c);
        if (!bridge.ready()) return 0;
        int attempted=0;
        for (String pkg:new String[]{"com.kakao.talk","com.google.android.gms","com.google.android.gsf"}) {
            bridge.exec("cmd appops set "+pkg+" RUN_ANY_IN_BACKGROUND default");
            bridge.exec("cmd appops set "+pkg+" RUN_IN_BACKGROUND default");
            bridge.exec("cmd appops set "+pkg+" WAKE_LOCK default");
            attempted++;
        }
        bridge.exec("cmd deviceidle whitelist -com.kakao.talk");
        p.edit().putBoolean("guardian_v212_notification_cleanup",true)
                .remove("critical_notification_fix_v210_done").apply();
        AppPrefs.setLastMessage(c,"과거 반복 적용하던 알림 앱 설정을 기본값으로 복구했습니다. 자동 관리는 충전/대기 중에만 실행됩니다.");
        return attempted;
    }

''' + x[b:]
x=x.replace('''        AppPrefs.setAutoManage(c,false);
        AppPrefs.setRestoreMode(c,true);''','''        AppPrefs.setAutoManage(c,false);
        AutoManageJobService.cancel(c);
        AppPrefs.setRestoreMode(c,true);''')
p.write_text(x,encoding="utf-8")

change("RuleConfig.java","public int autoScanMinutes = 30;","public int autoScanMinutes = 720;")
change("RuleConfig.java",
'r.autoScanMinutes = o.optInt("autoScanMinutes", r.autoScanMinutes);',
'r.autoScanMinutes = Math.max(720, o.optInt("autoScanMinutes", r.autoScanMinutes));')

p=root/"app/build.gradle"
x=p.read_text().replace("versionCode 20011","versionCode 20012").replace("versionName '2.0.11'","versionName '2.0.12'")
p.write_text(x)
p=root/"app/src/main/assets/rules_v200.json"
p.write_text(p.read_text().replace('"autoScanMinutes": 30','"autoScanMinutes": 720'))
p=root/"app/src/main/AndroidManifest.xml"
x=p.read_text()
needle='''        <service
            android:name=".UpdateJobService"'''
assert needle in x
x=x.replace(needle,'''        <service android:name=".AutoManageJobService"
            android:permission="android.permission.BIND_JOB_SERVICE"
            android:exported="true"/>
''' + needle)
p.write_text(x)

(src/"AutoManageJobService.java").write_text('''package com.mec.batteryguardian2;

import android.app.job.JobInfo;
import android.app.job.JobParameters;
import android.app.job.JobScheduler;
import android.app.job.JobService;
import android.content.ComponentName;
import android.content.Context;
import java.util.concurrent.ExecutorService;
import java.util.concurrent.Executors;

/** Charging-only, device-idle-friendly auto management without a persistent monitor. */
public class AutoManageJobService extends JobService {
    private static final int JOB_ID = 261012;
    private static final long INTERVAL_MS = 12L * 60L * 60L * 1000L;
    private ExecutorService worker;
    @Override public boolean onStartJob(JobParameters params) {
        if (!AppPrefs.autoManage(this) || AppPrefs.restoreMode(this)) return false;
        ShizukuBridge bridge = ShizukuBridge.get(this);
        bridge.ensureBound();
        worker = Executors.newSingleThreadExecutor();
        worker.execute(() -> {
            try {
                for (int i=0;i<10 && !bridge.ready();i++) Thread.sleep(300L);
                if (Thread.currentThread().isInterrupted() || !bridge.ready() || !UsageAccess.granted(this)
                        || !AppPrefs.autoManage(this) || AppPrefs.restoreMode(this)) return;
                PowerActions.restoreReusedApps(this);
                long now=System.currentTimeMillis();
                long last=AppPrefs.lastAutoScan(this);
                if (now-last >= INTERVAL_MS || last > now) {
                    SmartEngine.Result result=SmartEngine.analyze(this,true);
                    if (result.acted) AppPrefs.setLastMessage(this,result.explanation);
                    AppPrefs.setLastAutoScan(this,System.currentTimeMillis());
                }
            } catch (InterruptedException e) {
                Thread.currentThread().interrupt();
            } catch (Throwable ignored) {
            } finally {
                jobFinished(params,false);
                if(worker!=null) worker.shutdown();
            }
        });
        return true;
    }
    @Override public boolean onStopJob(JobParameters params) {
        if(worker!=null) worker.shutdownNow();
        return false;
    }
    public static void schedule(Context c) {
        if(!AppPrefs.autoManage(c))return;
        JobScheduler scheduler=(JobScheduler)c.getSystemService(Context.JOB_SCHEDULER_SERVICE);
        if(scheduler==null)return;
        JobInfo info=new JobInfo.Builder(JOB_ID,new ComponentName(c,AutoManageJobService.class))
                .setRequiresCharging(true)
                .setRequiresDeviceIdle(true)
                .setRequiresBatteryNotLow(true)
                .setPersisted(true)
                .setPeriodic(INTERVAL_MS)
                .build();
        scheduler.schedule(info);
    }
    public static void cancel(Context c) {
        JobScheduler scheduler=(JobScheduler)c.getSystemService(Context.JOB_SCHEDULER_SERVICE);
        if(scheduler!=null)scheduler.cancel(JOB_ID);
    }
}
''',encoding="utf-8")
print("v2.0.12 patch applied")
