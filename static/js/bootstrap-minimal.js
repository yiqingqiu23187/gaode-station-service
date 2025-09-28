/* Bootstrap 5 简化版本 JavaScript */

(function() {
    'use strict';

    // 警告框关闭功能
    function initAlerts() {
        document.addEventListener('click', function(e) {
            if (e.target.matches('.btn-close') || e.target.closest('.btn-close')) {
                const alert = e.target.closest('.alert');
                if (alert) {
                    alert.style.opacity = '0';
                    setTimeout(() => {
                        alert.remove();
                    }, 150);
                }
            }
        });
    }

    // 模态框功能（简化版）
    function initModals() {
        document.addEventListener('click', function(e) {
            if (e.target.matches('[data-bs-toggle="modal"]')) {
                const target = e.target.getAttribute('data-bs-target');
                const modal = document.querySelector(target);
                if (modal) {
                    modal.style.display = 'block';
                    modal.classList.add('show');
                    document.body.classList.add('modal-open');
                }
            }

            if (e.target.matches('.modal-backdrop') || e.target.matches('[data-bs-dismiss="modal"]')) {
                const modal = e.target.closest('.modal');
                if (modal) {
                    modal.style.display = 'none';
                    modal.classList.remove('show');
                    document.body.classList.remove('modal-open');
                }
            }
        });
    }

    // 下拉菜单功能（简化版）
    function initDropdowns() {
        document.addEventListener('click', function(e) {
            if (e.target.matches('[data-bs-toggle="dropdown"]')) {
                e.preventDefault();
                const menu = e.target.nextElementSibling;
                if (menu && menu.classList.contains('dropdown-menu')) {
                    menu.classList.toggle('show');
                }
            } else {
                // 点击其他地方关闭下拉菜单
                document.querySelectorAll('.dropdown-menu.show').forEach(menu => {
                    menu.classList.remove('show');
                });
            }
        });
    }

    // 折叠功能（简化版）
    function initCollapse() {
        document.addEventListener('click', function(e) {
            if (e.target.matches('[data-bs-toggle="collapse"]')) {
                e.preventDefault();
                const target = e.target.getAttribute('data-bs-target') || e.target.getAttribute('href');
                const element = document.querySelector(target);
                if (element) {
                    if (element.classList.contains('show')) {
                        element.classList.remove('show');
                        element.style.height = '0';
                    } else {
                        element.classList.add('show');
                        element.style.height = element.scrollHeight + 'px';
                    }
                }
            }
        });
    }

    // 工具提示功能（简化版）
    function initTooltips() {
        const tooltips = document.querySelectorAll('[data-bs-toggle="tooltip"]');
        tooltips.forEach(tooltip => {
            tooltip.addEventListener('mouseenter', function() {
                const title = this.getAttribute('title') || this.getAttribute('data-bs-title');
                if (title) {
                    const tooltipEl = document.createElement('div');
                    tooltipEl.className = 'tooltip fade show bs-tooltip-top';
                    tooltipEl.innerHTML = `
                        <div class="tooltip-arrow"></div>
                        <div class="tooltip-inner">${title}</div>
                    `;
                    document.body.appendChild(tooltipEl);

                    const rect = this.getBoundingClientRect();
                    tooltipEl.style.position = 'absolute';
                    tooltipEl.style.top = (rect.top - tooltipEl.offsetHeight - 5) + 'px';
                    tooltipEl.style.left = (rect.left + rect.width / 2 - tooltipEl.offsetWidth / 2) + 'px';
                    tooltipEl.style.zIndex = '1070';

                    this._tooltip = tooltipEl;
                }
            });

            tooltip.addEventListener('mouseleave', function() {
                if (this._tooltip) {
                    this._tooltip.remove();
                    this._tooltip = null;
                }
            });
        });
    }

    // 进度条动画
    function animateProgressBars() {
        const progressBars = document.querySelectorAll('.progress-bar');
        progressBars.forEach(bar => {
            const width = bar.style.width || bar.getAttribute('aria-valuenow') + '%';
            bar.style.width = '0%';
            setTimeout(() => {
                bar.style.width = width;
            }, 100);
        });
    }

    // 表单验证（简化版）
    function initFormValidation() {
        const forms = document.querySelectorAll('.needs-validation');
        forms.forEach(form => {
            form.addEventListener('submit', function(e) {
                if (!form.checkValidity()) {
                    e.preventDefault();
                    e.stopPropagation();
                }
                form.classList.add('was-validated');
            });
        });
    }

    // 轮播图功能（简化版）
    function initCarousels() {
        const carousels = document.querySelectorAll('.carousel');
        carousels.forEach(carousel => {
            const items = carousel.querySelectorAll('.carousel-item');
            const indicators = carousel.querySelectorAll('.carousel-indicators button');
            let currentIndex = 0;

            function showSlide(index) {
                items.forEach((item, i) => {
                    item.classList.toggle('active', i === index);
                });
                indicators.forEach((indicator, i) => {
                    indicator.classList.toggle('active', i === index);
                });
                currentIndex = index;
            }

            // 自动播放
            if (carousel.getAttribute('data-bs-ride') === 'carousel') {
                setInterval(() => {
                    const nextIndex = (currentIndex + 1) % items.length;
                    showSlide(nextIndex);
                }, 5000);
            }

            // 指示器点击
            indicators.forEach((indicator, index) => {
                indicator.addEventListener('click', () => showSlide(index));
            });

            // 控制按钮
            const prevBtn = carousel.querySelector('.carousel-control-prev');
            const nextBtn = carousel.querySelector('.carousel-control-next');

            if (prevBtn) {
                prevBtn.addEventListener('click', () => {
                    const prevIndex = currentIndex === 0 ? items.length - 1 : currentIndex - 1;
                    showSlide(prevIndex);
                });
            }

            if (nextBtn) {
                nextBtn.addEventListener('click', () => {
                    const nextIndex = (currentIndex + 1) % items.length;
                    showSlide(nextIndex);
                });
            }
        });
    }

    // 标签页功能
    function initTabs() {
        document.addEventListener('click', function(e) {
            if (e.target.matches('[data-bs-toggle="tab"]') || e.target.matches('[data-bs-toggle="pill"]')) {
                e.preventDefault();

                // 移除所有活动状态
                const tabList = e.target.closest('.nav');
                if (tabList) {
                    tabList.querySelectorAll('.nav-link').forEach(link => {
                        link.classList.remove('active');
                    });
                }

                // 添加当前活动状态
                e.target.classList.add('active');

                // 显示对应的内容
                const target = e.target.getAttribute('data-bs-target') || e.target.getAttribute('href');
                if (target) {
                    const tabContent = document.querySelector(target);
                    if (tabContent) {
                        // 隐藏所有标签页内容
                        const container = tabContent.closest('.tab-content');
                        if (container) {
                            container.querySelectorAll('.tab-pane').forEach(pane => {
                                pane.classList.remove('show', 'active');
                            });
                        }

                        // 显示当前标签页内容
                        tabContent.classList.add('show', 'active');
                    }
                }
            }
        });
    }

    // 初始化所有功能
    function init() {
        initAlerts();
        initModals();
        initDropdowns();
        initCollapse();
        initTooltips();
        initFormValidation();
        initCarousels();
        initTabs();
        animateProgressBars();
    }

    // DOM加载完成后初始化
    if (document.readyState === 'loading') {
        document.addEventListener('DOMContentLoaded', init);
    } else {
        init();
    }

    // 导出到全局对象（兼容性）
    window.Bootstrap = {
        init: init,
        initAlerts: initAlerts,
        initModals: initModals,
        initDropdowns: initDropdowns,
        initCollapse: initCollapse,
        initTooltips: initTooltips,
        initFormValidation: initFormValidation,
        initCarousels: initCarousels,
        initTabs: initTabs,
        animateProgressBars: animateProgressBars
    };

})();
