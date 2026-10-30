# S3.4 R09：成員與分攤唯一性

Spec：原 S3.4；使用者確認 15 名 active 上限包含 owner／登入成員／外部旅伴，所有加入入口共用。
沿用現有重新加入會恢復同一 member ID 的行為（包括 removed／soft-deleted）。NULL user_id 的外部旅伴不按姓名去重。
Constraints：新 migration 僅增加約束；發現既有重複則停止，不刪除／合併任何資料；只在專用 DB 測升級。

## Task 1: 防重複、防超限與安全升級

Interfaces：accept_invite／add_external_member 共用 trip row lock、active count；metadata 與 Alembic 必須一致。
1. DB regression：同 trip/user、同 transaction/member 重複 insert 被 DB 拒絕；並行同人加入只一 member；不同人／外部混合加入不超限。
   Expected: 缺約束／未鎖的案例 RED。
2. 保留 rejoin 同 member ID、同名外部旅伴與正常容量內加入。
   Expected: 既有行為不退化。
3. 新增 0019 unique constraints；migration 先檢查兩類重複，無資料改寫，重複時阻擋並保持舊 revision。
   Expected: 空庫、含資料 0018→head、兩種重複阻擋測試通過。
4. 用專用 runner 跑針對案例與完整 tests -q；Expected: 全套通過且零 skip。
5. 更新合約與部署限制，驗證後 commit，再同全套命令 task-done。
Review Focus：所有加入入口拿相同旅行鎖；重播／重新加入身份不變；unique 對已刪除的登入會員仍一致；多個 NULL 使用者不受誤擋；migration 不自動清資料、不改舊 migration。
