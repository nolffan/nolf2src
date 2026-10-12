/* Load our linked server.dll with its preferred base deliberately occupied,
 * so the loader must relocate it through its .reloc section, then stand
 * a real server up and tear it down: CreateServer runs CServerMgr::Init (the
 * banks, the hashes, the collections), DeleteServer runs Term. */
#include <windows.h>
#include <stdio.h>

typedef int  (*CreateServer_t)(int version, void* appGuid, void** ppServer);
typedef void (*DeleteServer_t)(void);

int main(int argc, char** argv)
{
    void* block;
    HMODULE h;
    CreateServer_t create;
    DeleteServer_t del;
    void* iface = 0;
    char guid[16] = {0};
    int rc;

    setvbuf(stdout, NULL, _IONBF, 0);   /* a crash must not eat the log */

    if (argc > 2)
    {
        block = VirtualAlloc((void*)0x10000000, 0x1000,
                             MEM_RESERVE, PAGE_NOACCESS);
        printf("base 0x10000000 %s\n", block ? "occupied" : "NOT occupied");
    }

    h = LoadLibraryA(argv[1]);
    if (!h) { printf("LoadLibrary FAILED: %lu\n", GetLastError()); return 1; }
    printf("loaded at %p%s\n", (void*)h,
           ((DWORD)h != 0x10000000) ? " (relocated)" : "");

    create = (CreateServer_t)GetProcAddress(h, "CreateServer");
    del    = (DeleteServer_t)GetProcAddress(h, "DeleteServer");
    if (!create || !del) { printf("exports missing\n"); return 1; }

    rc = create(2 /*SI_VERSION*/, guid, &iface);
    printf("CreateServer -> %d, interface %p\n", rc, iface);
    if (rc != 0 /*SI_OK*/ || !iface)
        return 1;

    del();
    printf("DeleteServer OK\n");
    return 0;
}
